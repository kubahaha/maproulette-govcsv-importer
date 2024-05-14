import requests


class Komoot:
    def query(query):
        url = f'https://photon.komoot.io/api?q={query}'
        resp = requests.get(url)

        try:
            resp_json = resp.json()
        except requests.exceptions.JSONDecodeError:
            print(f'ERROR! {resp.text}')
            raise

        if resp_json:
            try:
                return resp_json['features'][0]
            except KeyError:
                print(f'ERROR! {resp_json}')
                raise

    def result_2_latlon(result):
        return {
            'lat': result['geometry']['coordinates'][0],
            'lon': result['geometry']['coordinates'][1]
        }
