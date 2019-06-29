#!/usr/bin/env python
import argparse
import json
import os
import subprocess
import shutil
from pathlib import Path

HOME = str(Path.home())
PROJECT = 'eb-deploy-base'
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DROPBOX_DIR = os.path.join(HOME, 'Dropbox', 'settings', 'django', PROJECT)
SECRETS_DIR = os.path.join(ROOT_DIR, '.secrets')
PROJECTS = [
    'study-watson',
]

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--load', action='store_true')
parser.add_argument('-d', '--dump', action='store_true')
parser.add_argument('-f', '--force', action='store_true')
args = parser.parse_args()

ENV = dict(os.environ)


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, env=ENV, **kwargs)


if __name__ == '__main__':
    os.makedirs(SECRETS_DIR, exist_ok=True)

    if args.load:
        shutil.rmtree(SECRETS_DIR, ignore_errors=True)
        shutil.copytree(DROPBOX_DIR, SECRETS_DIR)
        # for project in PROJECTS:
        #     shutil.copytree(
        #         os.path.join(DROPBOX_DIR, project),
        #         os.path.join(SECRETS_DIR, project),
        #     )
    elif args.dump:
        shutil.rmtree(DROPBOX_DIR, ignore_errors=True)
        shutil.copytree(SECRETS_DIR, DROPBOX_DIR)
        # for project in PROJECTS:
        #     shutil.copytree(
        #         os.path.join(SECRETS_DIR, project),
        #         os.path.join(DROPBOX_DIR, project),
        #     )
