import os.path

from rich.tree import Tree
from rich import print as rprint
from rich.console import Console


error_console = Console(stderr=True, style="bold red")
console = Console()


def check_files(name, prepare, download):
    should_fail = False
    is_conf = '' if os.path.isfile(f'data/{name}/conf.py') else '[bold red] '
    is_gov = '' if os.path.isfile(f'data/{name}/gov.csv') else '[bold red] '

    if prepare:
        is_clean = '' if not os.path.isfile(f'data/{name}/gov_clean.csv') else '[bold yellow] '
    else:
        is_clean = '' if os.path.isfile(f'data/{name}/gov_clean.csv') else '[bold red] '

    if download:
        is_osm = '' if not os.path.isfile(f'data/{name}/data.osm') else '[bold yellow] '
        is_overpass = '' if (os.path.isfile(f'data/{name}/query.overpass') or os.path.isfile(f'data/{name}/query.overpassql')) else '[bold red] '
    else:
        is_osm = '' if os.path.isfile(f'data/{name}/data.osm') else '[bold red] '
        is_overpass = '' if (os.path.isfile(f'data/{name}/query.overpass') or os.path.isfile(f'data/{name}/query.overpassql')) else '[bold yellow] '

    is_out_coop = '' if not os.path.isfile(f'data/{name}/cooperative.osm') else '[bold red] '
    is_out_tf = '' if not os.path.isfile(f'data/{name}/tagfix.osm') else '[bold red] '

    console.log('[blue]Checking files...')
    tree = Tree('Expected files')
    workdir = tree.add('data').add(name)
    workdir.add(f'{is_conf}conf.py')
    workdir.add(f'{is_gov}gov.csv')
    workdir.add(f'{is_clean}gov_clean.csv')
    workdir.add(f'{is_osm}data.osm')
    workdir.add(f'{is_overpass}query.overpassql')
    workdir.add(f'{is_out_coop}{name}_cooperative.osm')
    workdir.add(f'{is_out_tf}{name}_tagfix.osm')

    if is_conf:
        error_console.log(f'{is_conf}Configuration file `data/{name}/conf.py` not found!')
        should_fail = True
    if is_gov:
        error_console.log(f'{is_gov}Source file with gov data `data/{name}/gov.csv` not found!')
        should_fail = True
    if is_clean:
        if prepare:
            console.log(f'{is_clean}Warning. File `input/{name}/gov_clean.csv` will be overwritten.')
        else:
            error_console.log(f'{is_clean}Source file with clean gov data `input/{name}/gov_clean.csv` not found! You can add `--prepare` argument to generate it.')
            should_fail = True
    if is_osm:
        if download:
            console.log(f'{is_osm}Warning. File `data/{name}/data.osm` will be overwritten')
        else:
            error_console.log(f'{is_osm}Source file with osm data `data/{name}/data.osm` not found! You can add `--download` argument to generate it.')
            should_fail = True
    if is_overpass:
        error_console.log(f'{is_overpass}Overpass query not saved in file `data/{name}/query.overpassql` (or `query.overpass`)!')
        should_fail = True
    if is_out_coop:
        error_console.log(f'{is_out_coop}Output file `data/{name}/cooperative.osm` needs to be deleted!')
        should_fail = True
    if is_out_tf:
        error_console.log(f'{is_out_tf}Output file `data/{name}/tagfix.osm` needs to be deleted!')
        should_fail = True

    rprint(tree)

    if should_fail:
        exit(1)
