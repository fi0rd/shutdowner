import aiohttp


class HTTPClient:
    def __init__(self, base_url: str, params: dict = None):
        self.base_url = base_url
        self.params = params if params else {}

__all__ = (
    'HTTPClient',
)
