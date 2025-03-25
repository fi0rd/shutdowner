from __future__ import annotations

import asyncio

from abc import ABC, abstractmethod
from services.services import incident_service, network_service
from db.models import Incidents
from enum import Enum
from sqlmodel import SQLModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
from core.logger import logger
from core.mt_bot import send_msg as mt_send_msg
from core.tg_bot import send_msg as tg_send_msg
from config.env import *


__all__ = (
    "start_handler",
)


class Role(Enum):
    core = 100
    aggregate = 40
    border = 30
    spine = 20
    edge = 10
    leaf = 10
    cache = 10
    peer = 1
    uplink = 1
    office = 1
    unclassified = 0

    def __gt__(self, other):
        return self.value > other.value

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def __get__(self, item):
        return self.value


class AbstractHandler(ABC):
    @abstractmethod
    def set_next(self, h: AbstractHandler) -> AbstractHandler:
        raise NotImplementedError(self.__class__.__name__ + ': not implemented')

    @abstractmethod
    async def handle(self, request):
        raise await NotImplementedError(self.__class__.__name__ + ': not implemented')


class BaseHandler(AbstractHandler):
    _next_handler = None

    def __init__(self, name=None):
        super().__init__()
        self.name = name

    def set_next(self, h: BaseHandler) -> BaseHandler:
        self._next_handler = h
        return h

    async def handle(self, request):
        if self._next_handler:
            return await self._next_handler.handle(request)
        return None

    @staticmethod
    def title_msg(handler_msg):
        return f'Alarm detected!\n\n{handler_msg}'

    @classmethod
    def create_chain(cls, name="default", chain=None):
        if not chain:
            return cls(name=name)

        created_handler = cls(name=name)
        current_handler = created_handler
        for handler in chain:
            current_handler = current_handler.set_next(handler())
        return created_handler


class ClassifiedSingleHandler(BaseHandler):
    stage = 'classification'

    async def handle(self, incident_item) -> SQLModel | None:
        logger.info(f'{self.__class__.__name__}: start...')
        logger.info(f'Incident__in_handle: [{type(incident_item)}] {incident_item}')
        incident_model = Incidents.sqlmodel_update(Incidents(), obj=incident_item)
        incident_model = self._set_incident_classname(incident_model)
        incident_model.stage = self.stage
        incident_model.running = True
        logger.info(f"incident_model: [{type(incident_model)}] {incident_model}")
        result_update = await incident_service().update(incident_model)
        logger.info(f'Incident classificator has completed. '
                    f'{self.__class__.__name__}: {incident_model}. '
                    f'Continue checking...')
        if not result_update:
            return None
        return incident_model

    @staticmethod
    def _set_incident_classname(incident) -> Incidents:
        incident.classname = HandlerClasses.unclassified.name
        edge_roles = ('edge', 'edge_minion', 'ddos_edge', 'edge_hadoop', 'edge_hosting', 'ext_edge')
        core_roles = ('core', 'ext_core', 'core_tarm_lan', 'core_p')
        aggregate_roles = ('aggregate', 'aggregate_hosting')
        border_roles = ('border',)
        cache_roles = ('cache',)
        all_roles = edge_roles + core_roles + aggregate_roles + border_roles
        role_h = incident.role_h
        role_p = incident.role_p

        if len(role_h.split(',')) > 1:
            role_h = Role(max(Role[role].value if role in all_roles else 0 for role in role_h.split(','))).name
            incident.role_h = role_h

        if len(role_p.split(',')) > 1:
            role_p = Role(max(Role[role].value if role in all_roles else 0 for role in role_p.split(','))).name
            incident.role_p = role_p

        conditions_mapping = {
            (HandlerClasses.peer_uplink.name, lambda: incident.link_type == 'P'),
            (HandlerClasses.aggregate_spine.name, lambda: (role_h in aggregate_roles and 'spine' in incident.peer) or
                                                          ('spine' in incident.hostname and role_p in aggregate_roles)),
            (HandlerClasses.spine_leaf.name, lambda: ('spine' in incident.hostname and 'leaf' in incident.peer) or
                                                     ('leaf' in incident.hostname and 'spine' in incident.peer)),
            (HandlerClasses.core_aggregate__access.name, lambda: (role_h in edge_roles and role_p in core_roles) or
                                                                 (role_h in core_roles and role_p in edge_roles) or
                                                                 (role_h in edge_roles and role_p in aggregate_roles) or
                                                                 (role_h in aggregate_roles and role_p in edge_roles)),
            (HandlerClasses.core__cache.name, lambda: (role_h in core_roles and role_p in cache_roles) or
                                                      (role_h in cache_roles and role_p in core_roles)),
            (HandlerClasses.core_aggregate_border.name, lambda: (role_h in core_roles and role_p in aggregate_roles) or
                                                                (role_h in aggregate_roles and role_p in core_roles) or
                                                                (role_h in core_roles and role_p in border_roles) or
                                                                (role_h in border_roles and role_p in core_roles) or
                                                                (role_h in core_roles and role_p in core_roles) or
                                                                (role_h in core_roles and role_p in core_roles) or
                                                                (role_h in border_roles and role_p in border_roles)),
        }

        for class_name, condition_func in conditions_mapping:
            if condition_func():
                logger.info(f"Incident classname: {class_name}")
                incident.classname = class_name
                break

        return incident


class CheckIncidentExistHandler(BaseHandler):
    stage = 'existence_check'

    # dummy
    async def handle(self, inc_model: SQLModel):
        logger.info(f'{self.__class__.__name__}: start...')
        is_exist_incident = False
        if is_exist_incident:
            logger.info(f'{self.__class__.__name__}: found duplicate incident in database')
            return None
        inc_model.stage = self.stage
        result = await incident_service().update(inc_model)
        logger.info(f'{self.__class__.__name__}: incident is not found in database. Continue...')
        return await super().handle(inc_model)


class CheckBandwidthHandler(BaseHandler):
    stage = 'bandwidth_check'

    # dummy
    async def handle(self, inc_model: SQLModel):
        logger.info(f'{self.__class__.__name__}: start...')
        is_bandwidth_ok = True
        if not is_bandwidth_ok:
            logger.info(f'{self.__class__.__name__}: bandwidth checking is FAIL. Stop...')
            return None
        inc_model.stage = self.stage
        inc_model.permit = True
        result = await incident_service().update(inc=inc_model)
        logger.info(f'{self.__class__.__name__}: bandwidth checking is OK. Continue...')
        return await super().handle(inc_model)


class PortShutdownHandler(BaseHandler):
    stage = 'port_shutdown'

    # dummy
    async def handle(self, inc_model: Incidents):
        time_from = int((inc_model.created_at - timedelta(minutes=25)).timestamp()*1000)
        time_to = min([int(datetime.now().timestamp()*1000), int((inc_model.created_at + timedelta(minutes=5)).timestamp()*1000)])
        grafana_in_errors_link = f"{CLICKHOUSE_DASHBOARD}?" \
                                 f"orgId=1&" \
                                 f"var-node={inc_model.hostname}&" \
                                 f"var-interface={inc_model.interface}&" \
                                 f"var-metric=InErrors&" \
                                 f"from={time_from}&to={time_to}"
        if inc_model.permit:
            handler_msg = f'{inc_model.metric_type}: {inc_model.metric_value}/sec\n' \
                          f'Classification: {inc_model.classname}\n' \
                          f'Required Action: shutdown interface\n'\
                          f'---\n'\
                          f'Link: {inc_model.hostname}  --  {inc_model.peer}\n' \
                          f'Interface: {inc_model.interface}\n\n' \
                          f'<a href="{grafana_in_errors_link}">click me</a>'
            msg = self.title_msg(handler_msg)
            mt_send_msg(chat_id=CHAT_ID, msg=msg, parse_mode="HTML")
            logger.info(f'{self.__class__.__name__}: start...')

            device_type = 'juniper_junos'

            # turn ON when will be access to network
            # result = await network_service(device_type=device_type).connect(host=inc_model.hostname)\
            #     .set_interface(inc_model.interface, action="down")

            inc_model.stage = self.stage
            result = await incident_service().update(inc=inc_model)
            logger.info(f'{self.__class__.__name__}: {msg}. Continue...')
        return await super().handle(inc_model)


class CreateJiraIncidentHandler(BaseHandler):
    stage = 'jira_create'

    # dummy
    async def handle(self, inc_model: SQLModel):
        logger.info(f'{self.__class__.__name__}: start...')
        inc_model.stage = self.stage
        result = await incident_service().update(inc=inc_model)
        logger.info(f'{self.__class__.__name__}: create new incident in Jira...')
        return await super().handle(inc_model)


peer_uplink_handler = BaseHandler.create_chain(name="peer_uplink",
                                               chain=(CheckIncidentExistHandler,
                                                      CheckBandwidthHandler,
                                                      PortShutdownHandler,
                                                      CreateJiraIncidentHandler))
core_aggregate__access_handler = BaseHandler.create_chain(name="core_aggregate__access",
                                                          chain=(CheckIncidentExistHandler,
                                                                 CheckBandwidthHandler,
                                                                 PortShutdownHandler,
                                                                 CreateJiraIncidentHandler))
core_aggregate_border_handler = BaseHandler.create_chain(name="core_aggregate_border",
                                                         chain=(CheckIncidentExistHandler,
                                                                CheckBandwidthHandler,
                                                                PortShutdownHandler,
                                                                CreateJiraIncidentHandler))
aggregate_spine_handler = BaseHandler.create_chain(name="aggregate_spine",
                                                   chain=(CheckIncidentExistHandler,
                                                          CheckBandwidthHandler,
                                                          PortShutdownHandler,
                                                          CreateJiraIncidentHandler))
spine_leaf_handler = BaseHandler.create_chain(name="spine_leaf",
                                              chain=(CheckIncidentExistHandler,
                                                     CheckBandwidthHandler,
                                                     PortShutdownHandler,
                                                     CreateJiraIncidentHandler))
core__cache_handler = BaseHandler.create_chain(name="core__cache",
                                               chain=(CheckIncidentExistHandler,
                                                      CheckBandwidthHandler,
                                                      PortShutdownHandler,
                                                      CreateJiraIncidentHandler))


class HandlerClasses(Enum):
    peer_uplink = peer_uplink_handler
    core_aggregate__access = core_aggregate__access_handler
    core_aggregate_border = core_aggregate_border_handler
    aggregate_spine = aggregate_spine_handler
    spine_leaf = spine_leaf_handler
    core__cache = core__cache_handler
    unclassified = None


async def start_handler() -> None:
    incident_items: List[Dict[str, Any]] = await incident_service().get_incidents_as_dict_with_filter(stage='initial',
                                                                                                      permit=False,
                                                                                                      running=False)
    logger.info(f'Found total incidents: {len(incident_items)}')

    if not incident_items:
        logger.info(f'There is not a new incidents')
        return None

    for incident_item in incident_items:
        logger.info(f'Found incident: {incident_item}')
        logger.info(f'Found incident type: {type(incident_item)})')

        incident_class = ClassifiedSingleHandler()
        incident = await incident_class.handle(incident_item)

        logger.info(f'Incident__in_start_handler: {incident}')

        match incident.classname:
            case HandlerClasses.peer_uplink.name:
                await HandlerClasses.peer_uplink.value.handle(incident)
            case HandlerClasses.core_aggregate__access.name:
                await HandlerClasses.core_aggregate__access.value.handle(incident)
            case HandlerClasses.core_aggregate_border.name:
                await HandlerClasses.core_aggregate_border.value.handle(incident)
            case HandlerClasses.aggregate_spine.name:
                await HandlerClasses.aggregate_spine.value.handle(incident)
            case HandlerClasses.spine_leaf.name:
                await HandlerClasses.spine_leaf.value.handle(incident)
            case HandlerClasses.core__cache.name:
                await HandlerClasses.core__cache.value.handle(incident)
            case _:
                logger.info(f'Unknown incident classname: {incident.classname}')
                return None


if __name__ == '__main__':
    asyncio.run(start_handler())
