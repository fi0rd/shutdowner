import aiohttp
from dependencies.cmdb import CMDBHttpClient
from config import CONFIG

__all__ = ('cmdb_client',
           )

CMDB_API_URL = CONFIG['cmdb']['url']
CMDB_API_USER = CONFIG['cmdb']['user']
CMDB_API_PASS = CONFIG['cmdb']['password']

cmdb_client = CMDBHttpClient(base_url=CMDB_API_URL,
                             params={
                                 "auth": aiohttp.BasicAuth(CMDB_API_USER, CMDB_API_PASS),
                                 "verify_ssl": False,
                                 "timeout": aiohttp.ClientTimeout(total=10)},
                             )
