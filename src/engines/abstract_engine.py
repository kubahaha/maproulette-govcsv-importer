import abc
from typing import Optional, Dict, Any
import logging

import requests
logger = logging.getLogger(__name__)


class AbstractEngine(abc.ABC):
    def __init__(self):
        self.header = {'User-Agent': 'maproulette-govcsv-importer/1.0'}

    def _get_json(self, url: str, params: Optional[Dict[str, str]] = None) -> Any:
        try:
            resp = requests.get(url, headers=self.header, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException:
            logger.exception("HTTP request failed: %s %s", url, params)
            raise
        except ValueError:
            logger.error("Error decoding JSON response from %s: %s", url, getattr(resp, "text", None))
            raise

    @abc.abstractmethod
    def query(self, query: str) -> dict:
        """Query the geocoding engine with the given query string."""

    @abc.abstractmethod
    def result_2_latlon(self, result: dict) -> dict:
        pass
