import logging

from src.converters import nominatim_addr

from .abstract_engine import AbstractEngine
logger = logging.getLogger(__name__)


class Nominatim(AbstractEngine):
    def __init__(self):
        super().__init__(rate_limit=1.0)

    def query(self, query: str, raise_exception=False) -> dict:
        try:
            data = self._get_json('https://nominatim.openstreetmap.org/search', params={'q': query, 'format': 'jsonv2'})
            if data:
                return data[0]
        except Exception:
            logger.exception("Error querying Nominatim for query: %s", query)
            if raise_exception:
                raise

        msg = f"Nominatim returned no results for query: {query}"
        logger.info(msg)
        if raise_exception:
            logger.error(msg)
            raise ValueError(msg)


    def result_2_latlon(self, result):
        return {
            'lat': result['lat'],
            'lon': result['lon']
        }

    def query_elements(self, ids: list[str]) -> dict:
        """Query multiple elements by their type + IDs."""
        url = 'https://nominatim.openstreetmap.org/lookup'
        try:
            data = self._rate_limited_request(url, params={'osm_ids': ",".join(ids), 'addressdetails': 1, 'format': 'jsonv2'})
        except Exception:
            logger.exception("Error querying Nominatim for elements: %s", ids)
            raise

        results = {}
        for item in data:
            results[item['osm_id']] = nominatim_addr(item)
        return results
