import os.path

from rich.tree import Tree
from rich import print as rprint
from rich.console import Console


error_console = Console(stderr=True, style="bold red")
console = Console()

def check_files(name, prepare):
    is_conf = '' if os.path.isfile(f'conf/{name}_conf.py') else '[bold red] '
    is_gov = '' if os.path.isfile(f'input/{name}_gov.csv') else '[bold red] '
    if prepare:
        is_clean = '' if not os.path.isfile(f'input/{name}_gov_clean.csv') else '[bold yellow] '
    else:
        is_clean = '' if os.path.isfile(f'input/{name}_gov_clean.csv') else '[bold red] '
    is_osm = '' if os.path.isfile(f'input/{name}.osm') else '[bold red] '
    is_out_coop = '' if not os.path.isfile(f'output/{name}_cooperative.osm') else '[bold red] '
    is_out_tf = '' if not os.path.isfile(f'output/{name}_tagfix.osm') else '[bold red] '

    console.log('[blue]Checking files...')
    tree = Tree("Expected files")
    tree.add('conf').add(f'{is_conf}{name}_conf.py')
    input = tree.add('input')
    input.add(f'{is_gov}{name}_gov.csv')
    input.add(f'{is_clean}{name}_gov_clean.csv')
    input.add(f'{is_osm}{name}.osm')
    output = tree.add('output')
    output.add(f'{is_out_coop}{name}_cooperative.osm')
    output.add(f'{is_out_tf}{name}_tagfix.osm')

    if is_conf:
        error_console.log(f'{is_conf}Configuration file `conf/{name}_conf.py` not found!')
    if is_gov:
        error_console.log(f'{is_gov}Source file with gov data `input/{name}_gov.csv` not found!')
    if is_clean:
        if prepare:
            console.log(f'{is_clean}Warning. File `input/{name}_gov_clean.csv` will be overwritten.')
        else:
            error_console.log(f'{is_clean}Source file with clean gov data `input/{name}_gov_clean.csv` not found! You can add `--prepare` argument to generate it.')
    if is_osm:
        error_console.log(f'{is_osm}Source file with osm data `input/{name}.osm` not found!')
    if is_out_coop:
        error_console.log(f'{is_out_coop}Output file `output/{name}_cooperative.osm` needs to be deleted!')
    if is_out_tf:
        error_console.log(f'{is_out_tf}Output file `output/{name}_tagfix.osm` needs to be deleted!')

    rprint(tree)
