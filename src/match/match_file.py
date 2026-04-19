from src.utils import WORKDIR


def save_matches(matches: dict[int, int], name: str):
    with open(f'{WORKDIR.format(name=name)}/matches.csv', 'w', encoding='utf-8') as f_out:
        f_out.write('__gov_id,__osm_id\n')
        for gov_id, osm_id in matches.items():
            f_out.write(f'{gov_id},{osm_id}\n')

def read_matches(name: str) -> dict[int, int]:
    matches = {}
    try:
        with open(f'{WORKDIR.format(name=name)}/matches.csv', 'r', encoding='utf-8') as f_in:
            next(f_in)
            for line in f_in:
                gov_id, osm_id = line.strip().split(',')
                matches[int(gov_id)] = int(osm_id)
    except FileNotFoundError:
        ...
    return matches
