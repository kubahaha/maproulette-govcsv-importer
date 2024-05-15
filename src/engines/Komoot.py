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

        if resp_json and resp_json.get('features'):
            try:
                return resp_json['features'][0]
            except (KeyError, IndexError):
                print(f'ERROR! for URL: `{url}`\n\n{resp_json}')
                raise

    def result_2_latlon(result):
        return {
            'lat': result['geometry']['coordinates'][1],
            'lon': result['geometry']['coordinates'][0]
        }
