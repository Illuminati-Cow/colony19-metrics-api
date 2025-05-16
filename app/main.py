from datetime import datetime
from fastapi import FastAPI, Depends
from pymongo import MongoClient
from pymongo.database import Database
from typing import Generator
import uuid
from models import *

DB_URI = "mongodb://localhost:27017"
DB_NAME = "metrics"

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