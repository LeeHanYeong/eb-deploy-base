#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess

import boto3 as boto3

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true')
parser.add_argument('--run', action='store_true')
parser.add_argument('--bash', action='store_true')
parser.add_argument('--eb', action='store_true')
args = parser.parse_args()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(ROOT_DIR, '.projects')
PROJECTS_REQUIREMENTS_DIR = os.path.join(ROOT_DIR, '.projects_requirements')

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

ENV = dict(os.environ, AWS_ACCESS_KEY_ID=ACCESS_KEY, AWS_SECRET_ACCESS_KEY=SECRET_KEY)


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, env=ENV, **kwargs)


if __name__ == '__main__':
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(PROJECTS_REQUIREMENTS_DIR, exist_ok=True)

    if args.eb:
        # 배포된 후 실행되는 스크립트
        # .projects/ 내부의 압축파일들을 /srv에 해
        os.makedirs(os.path.join(ROOT_DIR, '.log'), exist_ok=True)
        for project in PROJECTS:
            run(f'tar -xzvf /srv/project/.projects/{project}.tar.gz -C /srv')
        exit(0)

    for project in PROJECTS:
        project_dir = os.path.join(ROOT_DIR, project)
        project_requirements_dir = os.path.join(project_dir, '.requirements')
        project_secrets_dir = os.path.join(project_dir, '.secrets')

        # 각 프로젝트의 secrets를 Dropbox에서 받아와서, submodule dir에 추가
        # (gitignore에 있는 파일이므로 영향 없음)
        shutil.rmtree(project_secrets_dir, ignore_errors=True)
        shutil.copytree(
            os.path.join(DROPBOX_BASE, project),
            project_secrets_dir,
        )
        # 각 프로젝트 폴더에서 git pull 실행
        os.chdir(os.path.join(ROOT_DIR, project))
        run('git pull')

        # submodule프로젝트를 압축해서 .projects/ 폴더에 추가
        # 이후 배포하며 추가하고, 배포된 후 서버에서 압축을 푼다
        os.chdir(ROOT_DIR)
        run(f'tar cfvz .projects/{project}.tar.gz {project}')
        run(f'cp -rf {project_requirements_dir}/. {PROJECTS_REQUIREMENTS_DIR}/{project}/')

    run('docker pull python:3.7-slim')
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
    run('git add -f .projects/')
    run('git add -f .projects_requirements/')
    run('git add -f .secrets/')
    run('eb deploy --staged &')
    run('sleep 30')
    run('git reset HEAD', stdout=subprocess.DEVNULL)
