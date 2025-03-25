from fastapi import APIRouter, Depends
from typing import List, Annotated, Dict, Any

from db.models import Events, CMDBNetworkHost, Incidents
from services.services import incident_service, event_service, host_service, click_service, IncidentService, EventService, HostService
from dependencies.click_repo import ClickRepository
from dependencies import cmdb_client
from core.logger import logger


router = APIRouter(prefix="")


@router.get("/")
async def get_root(issue: str):
    return {"issue": issue}


@router.get("/cmdb/")
async def get_cmdb_request(
        *,
        host_srv: Annotated[HostService, Depends(host_service)],
):
    cmdb_host_objects: List[CMDBNetworkHost] = await cmdb_client.get_cmdb_model_objects()
    if not cmdb_host_objects:
        return {'error': 'CMDB unreachable'}
    await host_srv.add_hosts(cmdb_host_objects)
    await host_srv.backup()
    return {"total_hosts": len(cmdb_host_objects)}


@router.get("/events/inerrors/")
async def get_events_request(
        *,
        event_srv: Annotated[EventService, Depends(event_service)],
        click_srv: Annotated[ClickRepository, Depends(click_service)],
):
    events: List[Events] = await click_srv.get_events_inerrors()

    if events is None:
        return {"success": False,
                "error": "Connection error to clickhouse"}
    if not events:
        return {"success": True,
                "found": 0,
                "applied": 0,
                "message": "New events are not found"}
    logger.info(f"Total events: {len(events)}")
    events_added = await event_srv.add_events(events)
    return {"success": True,
            "found": len(events),
            "applied": len(events_added),
            "message": "Some events are not added" if len(events_added) < len(events) else "All events are added"}


@router.post("/add/")
async def add_incident(
        incident: Incidents,
        incident_srv: Annotated[IncidentService, Depends(incident_service)],
):
    inc_result = await incident_srv.add_incident(incident)
    return {"inc": inc_result}


@router.post("/incidents/")
async def create_incidents(
        *,
        event_srv: Annotated[EventService, Depends(event_service)],
        incident_srv: Annotated[IncidentService, Depends(incident_service)]):
    incidents = await incident_srv.fetch_incidents()
    await event_srv.delete_events_by_incidents(incidents)
    return incidents
