#!/usr/bin/env python
import json
import os
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS = json.load(open(os.path.join(ROOT_DIR, 'projects.json')))['PROJECTS']


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, **kwargs)


if __name__ == '__main__':
    for project in PROJECTS:
        run(f'DJANGO_SETTINGS_MODULE=config.settings.production /srv/env-{project}/bin/python3 /srv/{project}/app/manage.py collectstatic --noinput')
        run(f'DJANGO_SETTINGS_MODULE=config.settings.production /srv/env-{project}/bin/python3 /srv/{project}/app/manage.py migrate --noinput')
