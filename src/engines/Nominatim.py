import requests


class Nominatim:
    def query(query):
        url = f'https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2'.replace(' ', '+')
        resp = requests.get(url)

        try:
            resp_json = resp.json()
        except requests.exceptions.JSONDecodeError:
            print(f'ERROR! {resp.text}')
            raise

        if resp_json:
            return resp_json[0]

    def result_2_latlon(result):
        return {
            'lat': result['lat'],
            'lon': result['lon']
        }
