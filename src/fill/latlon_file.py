import csv

def save_latlon(latlons: dict[int, tuple[float, float]], name: str):
    with open(f'data/{name}/coords.csv', 'w', encoding='utf-8', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['__gov_id', 'lat', 'lon'])
        for gov_id, coords in latlons.items():
            writer.writerow([gov_id, coords[0], coords[1]])

def read_latlon(name: str) -> dict[int, tuple[float, float]]:
    latlons = {}
    try:
        with open(f'data/{name}/coords.csv', 'r', encoding='utf-8') as f_in:
            reader = csv.reader(f_in)
            next(reader)
            for row in reader:
                gov_id, lat, lon = row
                latlons[int(gov_id)] = (float(lat), float(lon))
    except FileNotFoundError:
        ...
    return latlons
