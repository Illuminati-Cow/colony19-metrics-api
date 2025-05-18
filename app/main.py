import os
from datetime import datetime
from fastapi import FastAPI, Depends
from pymongo import MongoClient
from pymongo.database import Database
from typing import Generator
import uuid
from models import *

DB_USER = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "root")
DB_PASS = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "password")
DB_HOST = os.environ.get("MONGO_HOST", "mongodb")
DB_NAME = os.environ.get("MONGO_INITDB_DATABASE", "metrics")
DB_PORT = os.environ.get("MONGO_PORT", "27017")


DB_URI = f"mongodb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?authSource=admin"

app = FastAPI()

def get_db() -> Generator[Database, None, None]:
    client = MongoClient(DB_URI)
    db = client[DB_NAME]
    try:
        yield db
    finally:
        client.close()

@app.post("/metrics/new_session", response_model=NewSessionResponse)
def create_session(sessionRequest: NewSessionRequest, db: Database = Depends(get_db)):
    session_id = str(uuid.uuid4())
    db.sessions.insert_one({
        "_id": session_id,
        "app_name": sessionRequest.app_name,
        "app_version": sessionRequest.app_version,
        "device_id": sessionRequest.device_id,
        "device_type": sessionRequest.device_type,
        "device_model": sessionRequest.device_model,
        "os": sessionRequest.os,
    })
    return NewSessionResponse(session_id=session_id)

@app.put("/metrics/{session_id}")
def update_session_metrics(session_id: str, metrics: SessionMetrics, db: Database = Depends(get_db)):
    # Fetch device_id from session document
    session_doc = db.sessions.find_one({"_id": session_id})
    device_id = session_doc.get("device_id") if session_doc else None

    # Prepare events and deaths for insertion
    event_fields = {
        'achievements_earned': 'achievement',
        'progress_times': 'progress',
        'terminals_scanned': 'terminal',
    }
    def prepare_inserts(field_map, data, extra_fields=None):
        to_insert, query = [], []
        for field, type_val in field_map.items():
            items = getattr(data, field, [])
            for item in items:
                q = {'session_id': session_id, 'type': type_val, 'name': getattr(item, 'name', None)}
                if extra_fields and 'time' in extra_fields:
                    q['time'] = getattr(item, 'time', None)
                query.append(q)
                doc = {
                    'session_id': session_id,
                    'device_id': device_id,
                    'type': type_val,
                    'name': getattr(item, 'name', None),
                    'time': getattr(item, 'time', None)
                }
                if extra_fields:
                    doc.update({k: getattr(item, k, None) for k in extra_fields if k not in doc})
                to_insert.append(doc)
        return to_insert, query

    # Handle events
    events_to_insert, event_query = prepare_inserts(event_fields, metrics)
    existing_events = set()
    if event_query:
        existing = db.events.find({'$or': event_query}, {'type': 1, 'name': 1, '_id': 0})
        for ev in existing:
            existing_events.add((ev['type'], ev['name']))
    filtered_events = [e for e in events_to_insert if (e['type'], e['name']) not in existing_events]
    if filtered_events:
        db.events.insert_many(filtered_events)

    # Handle deaths
    death_fields = {'deaths': 'death'}
    deaths_to_insert, death_query = prepare_inserts(death_fields, metrics, extra_fields=['position'])
    existing_deaths = set()
    if death_query:
        existing = db.deaths.find({'$or': death_query}, {'type': 1, 'time': 1, '_id': 0})
        for d in existing:
            existing_deaths.add((d['type'], d['time']))
    filtered_deaths = [d for d in deaths_to_insert if (d['type'], d['time']) not in existing_deaths]
    if filtered_deaths:
        db.deaths.insert_many(filtered_deaths)

    # Update start_time and end_time only
    update_fields = {}
    if metrics.start_time:
        update_fields['start_time'] = metrics.start_time
    if metrics.end_time:
        update_fields['end_time'] = metrics.end_time
    result = db.sessions.update_one(
        {"_id": session_id},
        {"$set": update_fields}
    )

    # Insert FPS samples
    if metrics.fps and len(metrics.fps) > 0:
        fps_docs = [
            {
                "session_id": session_id,
                "device_id": device_id,
                "time": datetime.now(),
                "fps": fps
            }
            for fps in metrics.fps
        ]
        db.fps_data.insert_many(fps_docs)

    if result.matched_count == 0:
        return {"error": "Session not found"}
    return {
        "status": "ok",
        "fps_count": len(metrics.fps) if metrics.fps else 0,
        "events_count": len(filtered_events),
        "deaths_count": len(filtered_deaths)
    }

@app.get("/metrics")
async def get_metrics(db: Database = Depends(get_db)):
    sessions = list(db.sessions.find({}, {"_id": 0}))
    return {"metrics": sessions}

@app.get("/")
async def root():
    return {"message": "Welcome to the Metrics Collector API!"}

@app.get("/health")
async def healthcheck(db: Database = Depends(get_db)):
    try:
        db.command('ping')
        return {"status": "ok"}
    except Exception:
        return {"status": "error"}