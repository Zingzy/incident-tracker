from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, get_db
from .models import Incident, Note
from .schemas import (
    IncidentCreate,
    IncidentDetail,
    IncidentOut,
    IncidentUpdate,
    InfoOut,
    NoteCreate,
    NoteOut,
    Severity,
    StatsOut,
    Status,
    StatusChange,
)

SEVERITIES = ["SEV1", "SEV2", "SEV3", "SEV4"]

incidents_created = Counter("incidents_created_total", "Incidents opened", ["severity"])
incidents_resolved = Counter("incidents_resolved_total", "Incidents moved to resolved")
time_to_resolve = Histogram(
    "incidents_time_to_resolve_seconds",
    "Seconds from opening to resolving an incident",
    buckets=(1, 10, 60, 300, 900, 1800, 3600, 4 * 3600, 12 * 3600, 24 * 3600),
)
incidents_open = Gauge("incidents_open", "Incidents not yet resolved, read from the database at scrape time")

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.state.db_factory = SessionLocal
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


def count_open() -> float:
    with app.state.db_factory() as db:
        return db.scalar(select(func.count(Incident.id)).where(Incident.status != "resolved")) or 0


incidents_open.set_function(count_open)


def find_incident(db: Session, incident_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/")
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "READY"}


@app.get("/api/info", response_model=InfoOut)
def info():
    return InfoOut(site_title=settings.site_title, environment=settings.environment, version=settings.app_version)


@app.get("/api/incidents", response_model=list[IncidentOut])
def list_incidents(
    status_filter: Status | None = Query(default=None, alias="status"),
    severity: Severity | None = None,
    service: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(Incident).order_by(Incident.id.desc())
    if status_filter:
        query = query.where(Incident.status == status_filter)
    if severity:
        query = query.where(Incident.severity == severity)
    if service:
        query = query.where(Incident.service == service)
    return list(db.scalars(query))


@app.post("/api/incidents", response_model=IncidentDetail, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    incident = Incident(**payload.model_dump(), status="open")
    incident.notes.append(Note(body=f"Opened as {payload.severity} on {payload.service}"))
    db.add(incident)
    db.commit()
    db.refresh(incident)
    incidents_created.labels(severity=payload.severity).inc()
    return incident


@app.get("/api/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    return find_incident(db, incident_id)


@app.put("/api/incidents/{incident_id}", response_model=IncidentDetail)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)):
    incident = find_incident(db, incident_id)
    for key, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(incident, key, value)
    db.commit()
    db.refresh(incident)
    return incident


@app.delete("/api/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    db.delete(find_incident(db, incident_id))
    db.commit()


@app.post("/api/incidents/{incident_id}/status", response_model=IncidentDetail)
def change_status(incident_id: int, payload: StatusChange, db: Session = Depends(get_db)):
    incident = find_incident(db, incident_id)
    if payload.status == incident.status:
        return incident
    if payload.status == "resolved":
        incident.resolved_at = datetime.now(timezone.utc)
        opened = incident.created_at if incident.created_at.tzinfo else incident.created_at.replace(tzinfo=timezone.utc)
        time_to_resolve.observe((incident.resolved_at - opened).total_seconds())
        incidents_resolved.inc()
    else:
        incident.resolved_at = None
    incident.notes.append(Note(body=f"Status {incident.status} -> {payload.status}"))
    incident.status = payload.status
    db.commit()
    db.refresh(incident)
    return incident


@app.get("/api/incidents/{incident_id}/notes", response_model=list[NoteOut])
def list_notes(incident_id: int, db: Session = Depends(get_db)):
    return find_incident(db, incident_id).notes


@app.post("/api/incidents/{incident_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def add_note(incident_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    incident = find_incident(db, incident_id)
    note = Note(body=payload.body)
    incident.notes.append(note)
    db.commit()
    db.refresh(note)
    return note


@app.get("/api/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Incident.severity, func.count(Incident.id)).where(Incident.status != "resolved").group_by(Incident.severity)
    ).all()
    by_severity = {severity: 0 for severity in SEVERITIES} | {severity: count for severity, count in rows}
    resolved = list(db.execute(select(Incident.created_at, Incident.resolved_at).where(Incident.status == "resolved")))
    durations = [(end - start).total_seconds() for start, end in resolved if end]
    mttr = sum(durations) / len(durations) if durations else None
    return StatsOut(open=sum(by_severity.values()), open_by_severity=by_severity, resolved=len(resolved), mean_time_to_resolve_seconds=mttr)
