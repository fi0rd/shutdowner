from typing import Optional

import redis

from settings import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD  # Import your Redis configuration


class RedisClient:
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def get_connection(self):
        """
        Establishes a connection to the Redis server and returns the client object.

        Uses a private attribute to store the connection and avoid redundant connections.
        """
        if self._client is None:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True  # Decode responses as strings for easier use
            )
        return self._client


redis_client = RedisClient()  # Create a global instance of the client

def get_redis():
    """
    Returns the Redis client object.

    Uses the global instance of RedisClient to access the connection.
    """
    return redis_client.get_connection()
