from datetime import datetime
from pydantic import BaseModel
from typing import Generator

class SessionMetrics(BaseModel):
    start_time: datetime
    end_time: datetime
    achievements_earned: dict[str, float]
    progress_times: dict[str, float]
    fps: list[int]
    terminals_scanned: dict[str, float]
    deaths: tuple[float, list[float]]

class NewSessionRequest(BaseModel):
    app_name: str
    app_version: str
    device_id: str
    device_type: str
    device_model: str
    os: str

class NewSessionResponse(BaseModel):
    session_id: str
