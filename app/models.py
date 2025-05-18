from collections import namedtuple
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

class DeathEvent(BaseModel):
    time: float
    position: List[float]

class Event(BaseModel):
    type: str
    name: str
    time: float

class SessionMetrics(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    achievements_earned: List[Event]
    progress_times: List[Event]
    fps: list[int]
    terminals_scanned: List[Event]
    deaths: List[DeathEvent]

class NewSessionRequest(BaseModel):
    app_name: str
    app_version: str
    device_id: str
    device_type: str
    device_model: str
    os: str

class NewSessionResponse(BaseModel):
    session_id: str

class FpsSample(BaseModel):
    session_id: str
    device_id: str
    time: datetime
    fps: int
