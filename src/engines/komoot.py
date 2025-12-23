import logging

from .abstract_engine import AbstractEngine
logger = logging.getLogger(__name__)


class Komoot(AbstractEngine):
    def query(self, query):
        data = self._get_json('https://photon.komoot.io/api', params={'q': query})
        features = data.get('features') if isinstance(data, dict) else None
        if not features:
            raise ValueError(f"Komoot returned no features for query: {query}")
        return features[0]

    def result_2_latlon(self, result):
        coords = result['geometry']['coordinates']
        return {
            'lat': coords[1],
            'lon': coords[0]
        }
