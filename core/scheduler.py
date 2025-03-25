# Run worker: arq core.scheduler.WorkerSettings

import aiohttp
import subprocess

from httpx import AsyncClient
from typing import Any
from db.init_db import init_db
from arq import cron
from aiohttp.client_exceptions import ClientConnectorError
from .logger import logger
from .handler import start_handler
from config.env import *
from requests.status_codes import codes


async def get_data_from_backend(url: str, log_msg: str, data=None, method="get") -> Any | None:
    logger.info(log_msg)
    try:
        async with aiohttp.ClientSession() as session:
            if method == "get":
                async with session.get(url) as response:
                    if response.status == codes.ok:
                        data = await response.json()
                        logger.info(f"GET request to {url} successful!: {data}")
                        return data
                    else:
                        logger.error(f"GET request to {url} failed with status {response.status}")
                        return None
            elif method == "post":
                async with session.post(url, json=data) as response:
                    if response.status == codes.ok:
                        data = await response.json()
                        logger.info(f"POST request to {url} successful! {data}")
                        return data
                    else:
                        logger.error(f"POST request to {url} failed with status {response.status}")
                        return None
            else:
                logger.error(f"Invalid method: {method}")
                return None
    except ClientConnectorError as e:
        logger.error(f"API connection error: {e}")
        return None


async def startup(ctx):
    logger.info(f"Scheduler: started ...")
    await init_db()
    ctx['session'] = AsyncClient()
    logger.info(f"Scheduler: init database ...")


async def shutdown(ctx):
    await ctx['session'].aclose()
    flush_redis_cache = subprocess.run(["redis-cli", "FLUSHDB"], capture_output=True, text=True)
    logger.info(f"Flush Redis cache: {flush_redis_cache.stdout}")
    logger.info(f"Scheduler: stopped ...")


async def scheduler_get_hosts(ctx):
    cmdb_url = f"{API_URL}/cmdb/"
    await get_data_from_backend(url=cmdb_url,
                                log_msg="Fetching hosts from CMDB")
    logger.info(f"Scheduler: get hosts by cron...")


async def scheduler_incidents(ctx):
    events_url = f"{API_URL}/events/inerrors/"
    events_result = await get_data_from_backend(url=events_url,
                                                log_msg="Fetching events from ClickHouse")
    logger.info(f"Events: {events_result}")
    if events_result and events_result.get('success') and events_result.get('count') != 0:
        create_url = f"{API_URL}/incidents/"
        await get_data_from_backend(url=create_url,
                                    log_msg="Fetching incidents",
                                    method="post")
    logger.info(f"Scheduler: get incidents by cron ...")


async def scheduler_handlers(ctx):
    await start_handler()
    logger.info(f"Scheduler: worker run by cron ...")


class WorkerSettings:
    on_startup = startup
    on_shutdown = shutdown
    cron_jobs = [
        cron(scheduler_incidents,
             run_at_startup=False,
             job_id='scheduler_incidents',
             second=20,
             # microsecond=1000,
             timeout=60),
        cron(scheduler_handlers,
             run_at_startup=False,
             job_id='scheduler_handlers',
             second=40,
             # microsecond=5000,
             timeout=60),
        cron(scheduler_get_hosts,
             run_at_startup=True,
             job_id='scheduler_get_hosts',
             minute=50,
             second=50,
             # microsecond=10000,
             timeout=60),
    ]
