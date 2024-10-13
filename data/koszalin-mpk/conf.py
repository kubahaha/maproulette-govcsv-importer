prepare = {
    "accept": lambda x: x.get('NOWA Nazwa przystanku') != 'LIKWIDACJA',
    "separator": ',',
    "tags": {
        'name': 'Nazwa przystanku',
        'new_name': 'NOWA Nazwa przystanku'
    }
}

matching = [
    ['name']
]

tags_to_delete = {}
tags_to_add = {}
tags_source = {}
tags_to_replace = {}

rules = {
    'update_addr': False,
    'download_latlon': True,
    'rewrite_tags': {
        'name': 'old_name',
        'new_name': 'name',
    }
}
