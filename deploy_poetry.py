#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass

import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true')
parser.add_argument('--run', action='store_true')
parser.add_argument('--bash', action='store_true')
parser.add_argument('--eb', action='store_true')
parser.add_argument('--install', action='store_true')
args = parser.parse_args()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.join(ROOT_DIR, '.archive')
POETRY_DIR = os.path.join(ROOT_DIR, '.poetry')

PROJECTS = [
    'washble',
]
AWS_PROFILE_SECRETS = 'lhy-secrets-manager'
AWS_PROFILE_EB = 'eb-deploy-base'
AWS_REGION = 'ap-northeast-2'

SESSION_SECRETS = boto3.session.Session(profile_name=AWS_PROFILE_SECRETS, region_name=AWS_REGION)
SESSION_SECRETS_CREDENTIALS = SESSION_SECRETS.get_credentials()
SESSION_EB = boto3.session.Session(profile_name=AWS_PROFILE_EB, region_name=AWS_REGION)
SESSION_EB_CREDENTIALS = SESSION_EB.get_credentials()

EB_ACCESS_KEY = SESSION_EB_CREDENTIALS.access_key
EB_SECRET_KEY = SESSION_EB_CREDENTIALS.secret_key
SECRETS_MANAGER_ACCESS_KEY = SESSION_SECRETS_CREDENTIALS.access_key
SECRETS_MANAGER_SECRET_KEY = SESSION_SECRETS_CREDENTIALS.secret_key

os.environ['AWS_ACCESS_KEY_ID'] = EB_ACCESS_KEY
os.environ['AWS_SECRET_ACCESS_KEY'] = EB_SECRET_KEY
ENV = dict(os.environ, AWS_ACCESS_KEY_ID=EB_ACCESS_KEY, AWS_SECRET_ACCESS_KEY=EB_SECRET_KEY)

# Docker Images
IMAGE_PRODUCTION_LOCAL = 'eb-deploy-base'
IMAGE_PRODUCTION_ECR = '469671560677.dkr.ecr.ap-northeast-2.amazonaws.com/eb-deploy-base:latest'

# Docker commands
RUN_OPTIONS = (
    f'-p 8000:80',
    f'--name {IMAGE_PRODUCTION_LOCAL}',
    f'--memory=1024m',
    f'--memory-swap=1536m',
    f'--cpus=1',
    f'{IMAGE_PRODUCTION_LOCAL}',
)
RUN_CMD = 'docker run --rm -it {options}'.format(
    options=' '.join([option for option in RUN_OPTIONS])
)


class Deploy:


def pre_deploy():
    os.chdir(ROOT_DIR)
    os.makedirs(POETRY_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)




@dataclass
class Project:
    name: str

    @property
    def repo_path(self):
        return os.path.join(ROOT_DIR, self.name)

    @property
    def poetry_path(self):
        return os.path.join(POETRY_DIR, self.name)

    @property
    def archive_file_path(self):
        return os.path.join(ARCHIVE_DIR, f'{self.name}.tar.gz')
