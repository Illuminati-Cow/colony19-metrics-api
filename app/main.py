from datetime import datetime
from unittest import result
from fastapi import FastAPI
from flask import session
from pydantic import BaseModel
from pymongo import MongoClient
import os

DB_URI = "mongodb://mongodb:27017"
DB_NAME = "metrics"

app = FastAPI()

# Initialize MongoDB client
client = MongoClient(DB_URI)
db = client[DB_NAME]

# Ensure collections exist
db.sessions.create_index("session_id", unique=True)

class SessionData(BaseModel):
    session_id: str
    app_name: str
    device: str
    os: str
    fps: list[int]


    

@app.post("/metrics/new_session")
def create_session(app_name: str):
    session_id = str(datetime.now())
    db.sessions.insert_one({
        "session_id": session_id,
        "app_name": app_name,
    })
    return {"status": "ok", "session_id": session_id}

# @app.put("/metrics/{session_id}")
# def update_data(session: SessionData):
#     db.sessions.update_one(
#         {"session_id": session.session_id},
#         {"$set": {
            
#         upsert=True
#     )
#     return {"status": "ok"}



@app.get("/metrics")
async def get_metrics():
    sessions = list(db.sessions.find({}, {"_id": 0}))
    return {"metrics": sessions}

@app.get("/")
async def root():
    return {"message": "Welcome to the Metrics Collector API!"}

@app.get("/health")
async def healthcheck():
    return {"status": "ok"}