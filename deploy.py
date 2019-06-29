#!/usr/bin/env python
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true')
parser.add_argument('--run', action='store_true')
parser.add_argument('--bash', action='store_true')
parser.add_argument('--eb', action='store_true')
parser.add_argument('--venv', action='store_true')
args = parser.parse_args()

HOME = str(Path.home())
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_DIR = os.path.join(ROOT_DIR, '.secrets')
DROPBOX_BASE = os.path.join(HOME, 'Dropbox', 'settings', 'django')

PROJECTS_DIR = os.path.join(ROOT_DIR, '.projects')
PROJECTS_REQUIREMENTS_DIR = os.path.join(ROOT_DIR, '.projects_requirements')
PROJECTS = [
    'study-watson',
]

try:
    SECRETS = json.load(open(os.path.join(SECRETS_DIR, 'secrets.json')))
    ACCESS_KEY = SECRETS['AWS_ACCESS_KEY_ID']
    SECRET_KEY = SECRETS['AWS_SECRET_ACCESS_KEY']
    ENV = dict(os.environ, AWS_ACCESS_KEY_ID=ACCESS_KEY, AWS_SECRET_ACCESS_KEY=SECRET_KEY)
except:
    ENV = dict(os.environ)


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, env=ENV, **kwargs)


if __name__ == '__main__':
    if args.venv:
        for project in PROJECTS:
            run(f'python3 -m venv /srv/env-{project}')
            run(f'/srv/env-{project}/bin/pip3 install'
                f' -r /tmp/projects_requirements/{project}/production.txt')
        exit(0)

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(PROJECTS_REQUIREMENTS_DIR, exist_ok=True)

    if args.eb:
        os.makedirs(os.path.join(ROOT_DIR, '.log'), exist_ok=True)
        for project in PROJECTS:
            run(f'tar -xzvf /srv/project/.projects/{project}.tar.gz -C /srv')
        exit(0)

    for project in PROJECTS:
        project_dir = os.path.join(ROOT_DIR, project)
        project_requirements_dir = os.path.join(project_dir, '.requirements')
        project_secrets_dir = os.path.join(project_dir, '.secrets')

        shutil.rmtree(project_secrets_dir)
        shutil.copytree(
            os.path.join(DROPBOX_BASE, project),
            project_secrets_dir,
        )
        run(f'tar cfvz .projects/{project}.tar.gz {project}')
        run(f'cp -rf {project_requirements_dir}/. {PROJECTS_REQUIREMENTS_DIR}/{project}/')

    run('docker build -t azelf/eb-deploy-base:base -f Dockerfile.base .')
    if args.build or args.run or args.bash:
        run('docker build -t eb-deploy-base .')
        if args.build:
            exit(0)

    if args.run:
        run('docker run --rm -it -p 8000:80 --name eb-deploy-base eb-deploy-base')
        exit(0)
    elif args.bash:
        run('docker run --rm -it -p 8000:80 --name eb-deploy-base eb-deploy-base /bin/bash')
        exit(0)

    run('docker push azelf/eb-deploy-base:base')
    run('git add -A')
    run('git add -f .secrets/')
    run('eb deploy --staged &')
    run('sleep 7')
    run('git reset HEAD', stdout=subprocess.DEVNULL)
