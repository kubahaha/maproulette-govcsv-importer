import logging

from .abstract_engine import AbstractEngine
logger = logging.getLogger(__name__)


class Nominatim(AbstractEngine):
    def query(self, query: str) -> dict:
        data = self._get_json('https://nominatim.openstreetmap.org/search',
                              params={'q': query, 'format': 'jsonv2'})
        if not data:
            raise ValueError(f"Nominatim returned no results for query: {query}")
        return data[0]


    def result_2_latlon(self, result):
        return {
            'lat': result['lat'],
            'lon': result['lon']
        }
