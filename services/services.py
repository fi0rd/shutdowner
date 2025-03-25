from typing import List, Dict, Any
from sqlalchemy.engine.result import ScalarResult

from db.models import SQLModel, Events, EventsUnknown
from db.service_repository import Incidents, IncidentsRepository, EventsRepository, HostsRepository
from network.connection import ConnectionFabric
from dependencies.click_repo import ClickRepository
from core.logger import logger


class NetworkService:

    def __init__(self, device_type):
        self.device_type = device_type

    def __new__(cls, device_type: str):
        return super().__new__(cls)

    def connect(self, host):
        return ConnectionFabric(self.device_type, host)


class IncidentService:
    def __init__(self):
        self.repo: IncidentsRepository = IncidentsRepository()

    async def add_incident(self, inc: SQLModel) -> SQLModel | None:
        inc = await self.repo.add_one(inc)
        return inc

    async def fetch_incidents(self) -> List[Dict[str, Any]]:
        return await self.repo.get_incidents()

    async def push_to_cache(self) -> List[Dict[str, Any]]:
        return await self.repo.push_cache()

    async def get_this_incident(self, incident: SQLModel) -> Dict[str, Any] | None:
        return await self.repo.get_explicit(incident)

    async def find_incident(self, hostname:str, interface:str) -> Incidents | None:
        return await self.repo.find_one(hostname, interface)

    async def pop_incident(self) -> ScalarResult | None:
        return await self.repo.pop()

    async def get_incident(self) -> ScalarResult | None:
        return await self.repo.get_one()

    async def get_incident_as_dict_with_filter(self, **filter_by) -> Dict[str, Any] | None:
        return await self.repo.get_one_as_dict_with_filter(**filter_by)

    async def get_incidents_as_dict_with_filter(self, **filter_by) -> List[Dict[str, Any]] | None:
        return await self.repo.get_all_as_dict_with_filter(**filter_by)

    async def update(self, inc: SQLModel) -> bool:
        return await self.repo.update(inc)


class HostService:
    def __init__(self, repo: HostsRepository):
        self.repo: HostsRepository = repo

    async def add_host(self, cmdb_host: SQLModel) -> SQLModel | None:
        return await self.repo.add_one(cmdb_host, filter_by={"NetworkType": "Switch"})

    async def add_hosts(self, cmdb_hosts: List[SQLModel]) -> None:
        for cmdb_host in cmdb_hosts:
            await self.repo.add_one(cmdb_host, filter_by={"NetworkType": "Switch"})

    async def backup(self):
        await self.repo.backup()


class EventService:
    def __init__(self):
        self.repo: EventsRepository = EventsRepository()

    async def add_event(self, event: SQLModel) -> SQLModel | None:
        return await self.repo.add_one(event)

    async def add_events(self, events: List[SQLModel]) -> List[Dict[str, Any]]:   # ,  incident_srv=Annotated[IncidentService, Depends(incident_service)]
        logger.info(f"EVENTS LEN: {len(events)}")
        events_list = []
        for event in events:
            inc_exists: Incidents = await incident_service().find_incident(event.hostname, event.interface)
            if not inc_exists:
                logger.info(f">>> >>> Add event: {event}")
                if await self.repo.add_one(event):  # filter_by={"link_type": "P"}
                    event_dict = event.model_dump(exclude={"id"})
                    events_list.append(event_dict)
                else:
                    logger.info(f">>> >>> Found old incident: {inc_exists}")
                    if self.repo.model_unknown:
                        event_data = event.model_dump(exclude={"uuid"}, exclude_unset=True)
                        event_unknown = EventsUnknown().sqlmodel_update(event_data)
                        print(f">>>  >>>  >>>  EVENT FAILED: {event_unknown}")
                        # filter_by =
                        if not await self.repo.get_one_as_dict_with_filter(model=self.repo.model_unknown,
                                                                           hostname=event_unknown.hostname,
                                                                           interface=event_unknown.interface):
                            await self.repo.add_one(event_unknown)
        return events_list

    async def delete_this_event(self, filter_by: dict) -> Events | None:
        return await self.repo.delete_explicit(**filter_by)

    async def delete_events_by_incidents(self, incidents: List[Dict[str, Any]]) -> List[Events] | None:
        deleted_events = []
        for inc in incidents:
            deleted_event = await self.delete_this_event(filter_by={"hostname": inc.get('hostname'), "interface": inc.get('interface')})
            deleted_events.append(deleted_event)
            logger.info(f">>> >>> Deleted event: {deleted_event}")
        return deleted_events


def click_service() -> ClickRepository:
    from config import CONFIG
    return ClickRepository(url=CONFIG['clickhouse']['host'],
                           port=CONFIG['clickhouse']['port'])


def event_service() -> "EventService":
    return EventService()


def incident_service() -> "IncidentService":
    return IncidentService()


def network_service(device_type) -> "NetworkService":
    return NetworkService(device_type)


def host_service() -> HostService:
    return HostService(HostsRepository())
