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

@app.put("/metrics/{session_id}", response_model=UpdateSessionResponse)
def update_session_metrics(session_id: str, metrics: SessionMetrics, db: Database = Depends(get_db)):
    # Fetch device_id from session document
    session_doc = db.sessions.find_one({"_id": session_id})
    device_id = session_doc.get("device_id") if session_doc else None

    def prepare_inserts(*items: EventRequest | DeathEventRequest):
        to_insert, query = [], []
        # Ensure device_id is always a string for document creation
        doc_device_id = device_id if device_id is not None else ""
        for item in items:
            if isinstance(item, EventRequest):
                doc = EventDoc(
                    session_id=session_id,
                    device_id=doc_device_id,
                    type=item.type,
                    name=item.name,
                    time=item.time
                ).model_dump()
                q = {'session_id': session_id, 'type': item.type, 'name': item.name}
            elif isinstance(item, DeathEventRequest):
                doc = DeathEventDoc(
                    session_id=session_id,
                    device_id=doc_device_id,
                    time=item.time,
                    position=item.position
                ).model_dump()
                q = {'session_id': session_id, 'time': item.time}
            else:
                continue
            query.append(q)
            to_insert.append(doc)
        return to_insert, query

    if db.sessions.count_documents({"_id": session_id}) == 0:
        return {"error": "Session not found"}
    # Handle events
    events_to_insert, event_query = prepare_inserts(*metrics.achievements_earned, *metrics.progress_times, *metrics.terminals_scanned)
    existing_events = set()
    if event_query:
        existing = db.events.find({'$or': event_query}, {'type': 1, 'name': 1, '_id': 0})
        for ev in existing:
            existing_events.add((ev['type'], ev['name']))
    filtered_events = [e for e in events_to_insert if (e['type'], e['name']) not in existing_events]
    if filtered_events:
        db.events.insert_many(filtered_events)

    # Handle deaths
    deaths_to_insert, death_query = prepare_inserts(*metrics.deaths)
    existing_deaths = set()
    if death_query:
        existing = db.deaths.find({'$or': death_query}, {'time': 1, '_id': 0})
        for d in existing:
            existing_deaths.add(d['time'])
    filtered_deaths = [d for d in deaths_to_insert if d['time'] not in existing_deaths]
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

    return UpdateSessionResponse(
        status="ok",
        fps_count=len(metrics.fps) if metrics.fps else 0,
        events_count=len(filtered_events),
        deaths_count=len(filtered_deaths)
    )

@app.get("/metrics", response_model=GetMetricsResponse)
async def get_metrics(db: Database = Depends(get_db)):
    sessions = list(db.sessions.find({}, {"_id": 0}))
    return GetMetricsResponse(metrics=sessions)

@app.get("/", response_model=RootResponse)
async def root():
    return RootResponse(message="Welcome to the Metrics Collector API!")

@app.get("/health", response_model=HealthCheckResponse)
async def healthcheck(db: Database = Depends(get_db)):
    try:
        db.command('ping')
        return HealthCheckResponse(status="ok")
    except Exception:
        return HealthCheckResponse(status="error")