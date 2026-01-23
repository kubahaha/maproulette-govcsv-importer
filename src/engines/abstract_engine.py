import abc
import time
from typing import Optional, Dict, Any
import logging

from rich.console import Console
import requests
logger = logging.getLogger(__name__)

console = Console()


class AbstractEngine(abc.ABC):
    def __init__(self, rate_limit: float = 1.0):
        self.header = {'User-Agent': 'maproulette-govcsv-importer/1.0'}
        self.rate_limit = rate_limit
        self._last_request_time = 0.0

    def _rate_limited_request(self, url: str, params: Optional[Dict[str, str]] = None) -> Any:
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 1 / self.rate_limit:
            time.sleep((1 / self.rate_limit) - elapsed)

        try:
            self._last_request_time = time.time()
            resp = requests.get(url, headers=self.header, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            logger.error("Request to %s timed out", url)
            raise
        except requests.exceptions.RequestException:
            logger.exception("HTTP request failed: %s %s", url, params)
            raise
        except ValueError:
            logger.error("Error decoding JSON response from %s: %s", url, getattr(resp, "text", None))
            raise

    def _get_json(self, url: str, params: Optional[Dict[str, str]] = None) -> Any:
        return self._rate_limited_request(url, params)

    @abc.abstractmethod
    def query(self, query: str) -> dict:
        """Query the geocoding engine with the given query string."""

    @abc.abstractmethod
    def result_2_latlon(self, result: dict) -> dict:
        pass

    def download_latlon(self, tags):
        found = False

        if tags.get("official_name"):
            found = self.query(tags["official_name"])

        if not found and (tags.get("addr:city") or tags.get("addr:place")) and tags.get("addr:street") and tags.get("addr:housenumber"):
            found = self.query(f'{tags.get("addr:street", tags.get("addr:place", ""))} {tags.get("addr:housenumber", "")} {tags.get("addr:city", "")} {tags.get("addr:postcode", "")}')

        if not found and (tags.get("addr:city") or tags.get("addr:place")) and tags.get("name") and tags.get("addr:housenumber"):
            found = self.query(f'{tags.get("addr:name", "")}, {tags.get("addr:city", tags.get("addr:place", ""))}, {tags.get("addr:postcode", "")}')

        if found:
            return self.result_2_latlon(found)
        console.log('No lat/lon found')
        return {}
