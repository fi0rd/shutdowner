# format:
# {"hostname":"x","interface":"x","description":"x","value":x}

import re
import sys
import hashlib
# import random
from collections import defaultdict

from typing import Iterable, Any, List
from config import CONFIG
from datetime import datetime, timedelta
from clickhouse_driver import Client as ClickHouseClient
from clickhouse_driver import errors as ClickHouseErrors
from db.models import Events
from core.logger import logger
from clickhouse_driver.errors import SocketTimeoutError


EXCLUDE_INTERFACES = ('vlanif', 'vlan', 'vl', 'irb',
                      'port-channel', 'ae', 'eth-trunk', 'po', 'bundle-ether',
                      'management', 'mgmt', 'fa', 'null',
                      'lo', 'eth[0-1]', 'bond[0-9]')
CLICK_URL = CONFIG['clickhouse']['host']
CLICK_PORT = CONFIG['clickhouse']['port']

MAX_INERRORS_THRESHOLD_LIMIT = CONFIG['clickhouse']['metric']['inerrors']['threshold_value_limit']
MAX_INERRORS_COUNTS = CONFIG['clickhouse']['metric']['inerrors']['threshold_counter_limit']
TIME_INTERVAL = CONFIG['clickhouse']['metric']['inerrors']['time_interval_minutes']
CLICK_DELAY = CONFIG['clickhouse']['metric']['inerrors'].get('delay_minutes') or 0


def _exclude_interfaces(interface: str) -> bool:
    return any(re.compile(f"{pattern}", re.IGNORECASE).match(interface) for pattern in EXCLUDE_INTERFACES)


class ClickRepository:
    def __init__(self, url, port=9000):
        self.client = ClickHouseClient(url, port=port, connect_timeout=30)

    @staticmethod
    def convert_speed_to_human_readable(speed_in_bps):
        units = ['bps', 'kbps', 'Mbps', 'Gbps']
        unit_index = 0
        while speed_in_bps >= 1000 and unit_index < len(units) - 1:
            speed_in_bps /= 1000
            unit_index += 1
        return f"{speed_in_bps:.2f} {units[unit_index]}"

    async def get_events_inoutoctets(self, hostname, interface, dev=False) -> str | None:
        global time_start, date_start
        date_start = datetime.today().strftime('%Y-%m-%d')
        query = f"SELECT quantile(0.99)(Value) FROM default.distributed_net_graphite PREWHERE Date = '2024-05-27' where like(Path, '%Octets%') and like(Path, '%{hostname}.interfaces.{interface}.%')"
        print(f'QUERY: {query}')
        time_start_time = datetime.fromtimestamp(int(1715469502))
        time_end_time = datetime.fromtimestamp(int(1715469872))
        metrics: List = self._get_clickhouse_metrics(query)
        if not metrics:
            logger.error(f'InOut metrics not found')
            return None
        in_out_octets_quantile_metric = self.convert_speed_to_human_readable(metrics[0][0])
        return in_out_octets_quantile_metric

    async def get_events_inerrors(self, dev=False) -> list[Events] | None:
        # dev
        #
        # 1.
        if not CONFIG['debug']['mode']:
            date_now = datetime.now()
            date_start = datetime.today().strftime('%Y-%m-%d')
            time_start = int((date_now - timedelta(minutes=TIME_INTERVAL, seconds=10)).timestamp()) - CLICK_DELAY * 60
            time_end = int(date_now.timestamp()) - CLICK_DELAY * 60
        else:
            date_start = CONFIG['debug']['date_start']
            time_start = CONFIG['debug']['time_start']
            time_end = CONFIG['debug']['time_end']
        #
        # dev end
        query = f"SELECT * FROM default.distributed_net_graphite PREWHERE Date = '{date_start}' and Timestamp > {time_start} and Timestamp < {time_end} where like(Path, '%InErrors%') and (like(Path, '%-I-%') or like(Path, '%-P-%') or like(Path, '%-U-%')) ORDER BY Timestamp"
        t1 = datetime.fromtimestamp(time_start).strftime("%Y-%m-%d %H:%M:%S")
        t2 = datetime.fromtimestamp(time_end).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f'QUERY: {query}\nfrom {t1} to {t2}')
        try:
            metrics: List = self._get_clickhouse_metrics(query)
        except SocketTimeoutError:
            logger.error(f'SocketTimeoutError: {query}')
            return None
        if not metrics:
            return []

        events = list()
        inerrors_count = defaultdict(int)
        for metric in metrics:
            metric_path = metric[0]
            metric_dict = self._parse_metric(metric_path)
            if not metric_dict:
                continue
            try:
                metric_value = round(metric[1])
            except (OverflowError, ValueError):
                metric_value = 0
            metric_timestamp = metric[4]
            if metric_value < MAX_INERRORS_THRESHOLD_LIMIT:
                inerrors_count[metric_dict['hash']] = 0
                continue
            if _exclude_interfaces(metric_dict['interface']):
                continue
            # TODO: check down interface
            #
            if metric_dict['description'] == 'None':
                continue

            peer = None
            flag_pattern = re.compile(r"-([A-Z])-")
            link_types = flag_pattern.findall(metric_dict['description'])
            if link_types:
                link_type = link_types[0].strip()
            else:
                continue
            new_description = flag_pattern.sub(r"", metric_dict['description']).lstrip('_')
            description_split = new_description.split('_')
            if description_split:
                peer = description_split[0]
            inerrors_count[metric_dict['hash']] += 1
            msg = f"Hostname: {metric_dict['hostname']}, " \
                  f"Interface: {metric_dict['interface']}, " \
                  f"Value: {metric_value}, " \
                  f"Count: {inerrors_count[metric_dict['hash']]} " \
                  f"Date: {datetime.fromtimestamp(metric_timestamp)}"
            logger.info('!!!  ' + msg)
            if inerrors_count[metric_dict['hash']] == MAX_INERRORS_COUNTS:
                event = Events(type="InErrors",
                               hostname=metric_dict['hostname'],
                               interface=metric_dict['interface'],
                               description=metric_dict['description'],
                               link_type=link_type or "",
                               peer=peer or "",
                               value=str(metric_value),
                               created_at=datetime.fromtimestamp(metric_timestamp))
                events.append(event)
                logger.info('>>>  ' + msg)
        if dev:
            print('!!! DEV !!!')
            print(events)
            print('!!! DEV END !!!')
        return events

    def _get_clickhouse_metrics(self, query: str):
        try:
            response = self.client.execute(query)
        except ClickHouseErrors.NetworkError as err:
            text = f'ERROR: clickhouse connection failed: {err}'
            print(text)
            return False
        except KeyboardInterrupt:
            print('\nterminate script process by Ctrl-C\n')
            sys.exit(1)
        return response

    @staticmethod
    def _parse_metric(metric):
        pattern = r'^(.*?)\.interfaces\.(.*?)\.(.*?)\.(.*)$'
        match = re.match(pattern, metric)

        if match:
            hostname = match.group(1)  
            interface = match.group(2) 
            description = match.group(3)
            event_type = match.group(4) 

            if not all((bool(hostname), bool(interface), bool(description), bool(event_type))):
                return None

            return {
                'hostname': hostname,
                'interface': interface,
                'description': description,
                'type': event_type,
                'hash':  hashlib.sha256(f"{hostname}:{interface})".encode()).hexdigest()
            }
        else:
            # print(f"Unknown metric: {metric}")
            return None


if __name__ == '__main__':
    click_repo = ClickRepository(url=CLICK_URL, port=CLICK_PORT)
    click_repo.get_events_inerrors(dev=True)
    

