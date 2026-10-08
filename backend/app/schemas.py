from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["SEV1", "SEV2", "SEV3", "SEV4"]
Status = Literal["open", "investigating", "resolved"]


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=80)
    severity: Severity


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    service: str | None = Field(default=None, min_length=1, max_length=80)
    severity: Severity | None = None


class StatusChange(BaseModel):
    status: Status


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class NoteOut(BaseModel):
    id: int
    body: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class IncidentOut(BaseModel):
    id: int
    title: str
    service: str
    severity: Severity
    status: Status
    created_at: datetime
    resolved_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class IncidentDetail(IncidentOut):
    notes: list[NoteOut]


class StatsOut(BaseModel):
    open: int
    open_by_severity: dict[str, int]
    resolved: int
    mean_time_to_resolve_seconds: float | None


class InfoOut(BaseModel):
    site_title: str
    environment: str
    version: str
