from collections import namedtuple
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

class DeathEventRequest(BaseModel):
    time: float
    position: List[float]

class DeathEventDoc(DeathEventRequest):
    session_id: str
    device_id: str

class EventRequest(BaseModel):
    type: str
    name: str
    time: float

class EventDoc(EventRequest):
    session_id: str
    device_id: str

class SessionMetrics(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    achievements_earned: List[EventRequest]
    progress_times: List[EventRequest]
    fps: list[int]
    terminals_scanned: List[EventRequest]
    deaths: List[DeathEventRequest]

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

class UpdateSessionResponse(BaseModel):
    status: str
    fps_count: int
    events_count: int
    deaths_count: int

class GetMetricsResponse(BaseModel):
    metrics: list

class RootResponse(BaseModel):
    message: str

class HealthCheckResponse(BaseModel):
    status: str
