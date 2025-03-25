from __future__ import annotations

import sys

from netmiko.juniper.juniper import JuniperSSH
from config import CONFIG
from core.logger import logger

__all__ = ('ConnectionFabric',
           'JuniperConnection',
           )


class JuniperConnection:

    def __init__(self, host, *args, **kwargs):
        self.host = host
        self.username = CONFIG['network']['username']

    async def set_interface(self, interface, action="down", check_state=False):
        action_map = {"down": "set", "up": "delete"}
        try:
            with JuniperSSH(device_type='juniper_junos',
                            host=self.host,
                            username=self.username,
                            allow_agent=True, use_keys=False) as conn:
                if check_state:
                    command = f"show int {interface} brief | display xml | match admin-status"
                    show_output = conn.send_command(command)
                    logger.debug(show_output)
                    if action == "up" and "up" in show_output:
                        logger.error("WARNING --- interface: ", interface, "of switch: ", self.host, "is already UP")
                        sys.exit("Interface is already UP")
                    if action == "down" and "down" in show_output:
                        logger.error("WARNING --- interface: ", interface, "of switch: ", self.host, "is already DOWN")
                        sys.exit("Interface is already DOWN")
                config_command = f"{action_map[action]} interfaces {interface} disable"
                logger.debug("do command: ", config_command)
                conn.config_mode(config_command="configure exclusive")
                if conn.check_config_mode():
                    print('Enter config mode...')
                    shutdown_output = conn.send_command(command_string=config_command, expect_string=r".*#", read_timeout=60)
                    print("output:\n", shutdown_output)
                    save_config_output = conn.commit(and_quit=True, read_timeout=60)
                    print(save_config_output)
                conn.disconnect()
        except Exception as e:
            raise Exception(f'Cannot connect to switch: {self.host}')


class ConnectionFabric:
    CLASS_MAPPER = {
        'juniper_junos': JuniperConnection
    }

    def __new__(cls, device_type, host, *args, **kwargs):
        platforms = list(cls.CLASS_MAPPER.keys())
        if device_type not in platforms:
            raise ValueError(
                f"Unsupported device type {device_type}. Currently supported platforms are: {platforms}"
            )
        connection_class = cls.CLASS_MAPPER[device_type]
        return connection_class(host, *args, **kwargs)




