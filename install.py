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
        run(f'python3 -m venv /srv/env-{project}')
        run(f'/srv/env-{project}/bin/pip3 install'
            f' -r /tmp/projects_requirements/{project}/production.txt')
