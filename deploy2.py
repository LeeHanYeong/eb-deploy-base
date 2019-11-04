#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess

import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true')
parser.add_argument('--run', action='store_true')
parser.add_argument('--bash', action='store_true')
parser.add_argument('--eb', action='store_true')
args = parser.parse_args()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(ROOT_DIR, '.projects')
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


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, env=ENV, **kwargs)


def build():
    os.chdir(ROOT_DIR)


if __name__ == '__main__':
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(POETRY_DIR, exist_ok=True)

    if args.eb:
        # 배포된 후 실행되는 스크립트
        # .projects/ 내부의 압축파일들을 /srv에 해
        os.makedirs(os.path.join(ROOT_DIR, '.log'), exist_ok=True)
        for project in PROJECTS:
            run(f'tar -xzvf /srv/project/.projects/{project}.tar.gz -C /srv')
        exit(0)

    for project in PROJECTS:
        project_dir = os.path.join(ROOT_DIR, project)
        project_poetry_dir = os.path.join(POETRY_DIR, project)
        os.makedirs(project_poetry_dir)

        # 각 프로젝트 폴더에서 git pull 실행
        os.chdir(os.path.join(ROOT_DIR, project))
        run('git pull')

        # poetry.lock, pyproject.toml을 프로젝트별로 복사
        shutil.copy(
            os.path.join(project_dir, 'poetry.lock'),
            os.path.join(project_poetry_dir),
        )
        shutil.copy(
            os.path.join(project_dir, 'pyproject.toml'),
            os.path.join(project_poetry_dir),
        )

        # submodule프로젝트를 압축해서 .projects/ 폴더에 추가
        # 이후 배포하며 추가하고, 배포된 후 서버에서 압축을 푼다
        os.chdir(ROOT_DIR)
        run(f'tar cfvz .projects/{project}.tar.gz {project}')

    run(f'docker pull python:3.7-slim')
    run(f'docker build -t {IMAGE_PRODUCTION_LOCAL}:base -f Dockerfile.base .')

    if args.build or args.run or args.bash:
        run(f'docker build -t {IMAGE_PRODUCTION_LOCAL} .')
        if args.build:
            exit(0)

    if args.run:
        run(f'{RUN_CMD}')
        exit(0)
    elif args.bash:
        run(f'{RUN_CMD} /bin/bash')
        exit(0)

    run('git add -A')
    run('git add -f .projects/')
    run('git add -f .projects_requirements/')
    run('git add -f .secrets/')
    run('eb deploy --staged &')
    run('sleep 30')
    run('git reset HEAD', stdout=subprocess.DEVNULL)
