import aiohttp

from typing import List, Dict
from db.models import CMDBNetworkHost
from .http_interface import HTTPClient


class CMDBHttpClient(HTTPClient):
    def __init__(self, base_url: str, params: dict = None,):
        super().__init__(base_url, params)

    async def _get_cmdb_items(self, query: str) -> List[Dict]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(query, **self.params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"CMDB request failed with status {response.status}.")
                        return []
        except Exception as error:
            print(f'CMDB connection error [{self._get_cmdb_items.__name__}]. {error}')
            return []

    async def get_cmdb_model_objects(self, dev=False) -> list[CMDBNetworkHost] | None:
        from config.config import CMDB_FILTER
        query = f"{self.base_url}hosts?$" \
                f"select=HostName, NodeMember, Status, Interfaces, HardwareModelName, OrgUnitName, NetworkType, NetworkRoles, DataCenterLocation, DataCenterLocationId&$" \
                f"expand=Interfaces($select = Ip)&$" \
                f"filter={CMDB_FILTER}"
        print(query)
        cmdb_hosts: List[Dict] = await self._get_cmdb_items(query=query)

        if not cmdb_hosts:
            raise Exception('CMDB unreachable')

        hosts_list = []
        for item in cmdb_hosts:
            new_item = {key: value for key, value in item.items() if key not in ['Interfaces']}
            new_item['Interfaces'] = ','.join(ip_dict.get('Ip') for ip_dict in item['Interfaces'] if
                                              ip_dict['Ip'] is not None)
            if isinstance(item['NetworkRoles'], list):
                new_item['NetworkRoles'] = ','.join(item['NetworkRoles'])
            if not new_item['NetworkRoles']:
                continue
            if '_' in new_item['HostName']:
                new_item['HostName'] = new_item['HostName'].split('_')[0]

            host = CMDBNetworkHost(HostName=new_item['HostName'],
                                   NodeMember=new_item['NodeMember'],
                                   Status=new_item['Status'],
                                   Interfaces=new_item.get('Interfaces'),
                                   HardwareModelName=new_item['HardwareModelName'],
                                   OrgUnitName=new_item['OrgUnitName'],
                                   NetworkType=new_item['NetworkType'],
                                   NetworkRoles=new_item['NetworkRoles'],
                                   DataCenterLocation=new_item['DataCenterLocation'],
                                   DataCenterLocationId=new_item['DataCenterLocationId'])

            hosts_list.append(host)

        if dev:
            print('!!! DEV !!!')
            print(f'Total hosts: {len(cmdb_hosts)}')
            print(cmdb_hosts[0])
            print('!!! DEV END !!!')
        return hosts_list

    async def fill_cmdb(self):
        from services.services import host_service
        try:
            cmdb_host_objects: List[CMDBNetworkHost] = await self.get_cmdb_model_objects()
        except Exception as err:
            print(f'CMDB connection error [{self.get_cmdb_model_objects.__name__}]. {err}')
            return {'error': 'CMDB unreachable'}
        if not cmdb_host_objects:
            return {'error': 'CMDB unreachable'}

        await host_service().add_hosts(cmdb_host_objects)
        await host_service().backup()
