import os
import shutil
from src.utils import WORKDIR


def prepare_workspace(name: str):
    workdir = WORKDIR.format(name=name)

    if os.path.exists(workdir):
        shutil.rmtree(workdir)

    os.makedirs(workdir)

    shutil.copy(f'data/{name}/gov_clean.csv', f'{workdir}/gov.csv')
    shutil.copy(f'data/{name}/data.osm', f'{workdir}/data.osm')
