from pydantic import BaseModel
from datetime import datetime


class BaseEvent(BaseModel):
    type: str
    hostname: str
    interface: str
    description: str
    link_type: str
    peer: str
    value: int


class BaseIncident(BaseModel):
    id: int
    event_id: int
    hostname: str
    interface: str
    link_type: str
    peer: str
    status_h: str
    status_p: str
    role_h: str
    role_p: str
    metric_type: str
    metric_value: str
    assigned_to: str
    created_at: datetime
    priority: str
    stage: str
    running: bool
