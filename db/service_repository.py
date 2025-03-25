from sqlmodel import text
from db.sql_repository import SQLModelRepository
from db.models import CMDBNetworkHost, CMDBNetworkHostBackup, Events, EventsUnknown
from db.session import async_session
from typing import List, Dict, Any
from db.models import Incidents
from pydantic_core import ValidationError
from core.logger import logger


class HostsRepository(SQLModelRepository):
    model = CMDBNetworkHost
    model_backup = CMDBNetworkHostBackup
    events = Events

    async def backup(self):
        truncate_backup_sql_query = f"TRUNCATE TABLE {self.model_backup.__name__.lower()} CASCADE;"
        fill_backup_sql_query = f"INSERT INTO {self.model_backup.__name__.lower()} SELECT * FROM {self.model.__name__.lower()};"
        async with async_session() as session:
            async with session.begin():
                await session.execute(text(truncate_backup_sql_query))
                await session.execute(text(fill_backup_sql_query))
                await session.commit()


class HostsBackupRepository(SQLModelRepository):
    model = CMDBNetworkHostBackup


class EventsRepository(SQLModelRepository):
    model = Events
    model_unknown = EventsUnknown


class IncidentsRepository(SQLModelRepository):
    model = Incidents

    async def get_incidents(self) -> List[Dict[str, Any]]:
        incidents_list = []
        async with async_session() as session:
            async with session.begin():
                incidents = await session.execute(text("""
                SELECT DISTINCT ON (e.uuid, e.hostname, e.interface)
                    e.uuid as event_id,
                    e.hostname,                
                    e.interface,
                    e.link_type,
                    e.peer,
                    h1."Status" as status_h,
                    COALESCE(h2."Status",'') as status_p,
                    h1."NetworkRoles" as role_h,
                    COALESCE(h2."NetworkRoles",'') as role_p,  
                    h1."HardwareModelName" as model_h,
                    h2."HardwareModelName" as model_p,
                    'undefined' as classname,          
                    e.type as metric_type,
                    e.value as metric_value,
                    'undefined' AS assigned_to,
                    e.created_at,
                    'Critical' AS priority,  -- CASE WHEN e.value > 100 THEN 'Critical' ELSE 'Low' END AS priority, 
                    'initial' AS stage,
                    FALSE AS permit,
                    FALSE AS running                                              
                FROM CMDBNetworkHostBackup h1
                INNER JOIN Events e ON e.hostname = h1."HostName"
                LEFT JOIN CMDBNetworkHostBackup h2 ON e.peer = h2."HostName"
                WHERE h1."Status" = 'Production' AND (h2."Status" = 'Production' OR h2."Status" IS NULL)
                --   AND (h2."HostName" IS NULL OR h2."HostName" IS NOT NULL)
                ORDER BY e.hostname, e.interface    
                -- ORDER BY e.interface
                """))
                # print(f'>>> __INCIDENTS__: {incidents.one_or_none()}')
                for inc_model in incidents.all():
                    print(f'>>> INC MODEL IS: {type(inc_model)}  {inc_model}')
                    try:
                        inc_model_valid = Incidents.model_validate(inc_model)
                    except ValidationError as e:
                        print(f'>>> ValidationError')
                        logger.error(f'>>> ERROR: {e}')
                        continue
                    inc_dict = inc_model_valid.model_dump(exclude={"uuid"})
                    incidents_list.append(inc_dict)
                    await self.add_one(inc_model_valid)
        return incidents_list

    async def push_cache(self) -> List[Dict[str, Any]]:
        raise NotImplementedError()

