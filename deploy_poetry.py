#!/usr/bin/env python
import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path

import boto3
from PyInquirer import prompt

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true')
parser.add_argument('--run', action='store_true')
parser.add_argument('--bash', action='store_true')
parser.add_argument('--eb', action='store_true')
parser.add_argument('--install', action='store_true')
args = parser.parse_args()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(ROOT_DIR, 'projects')
ARCHIVE_DIR = os.path.join(ROOT_DIR, '.archive')
POETRY_DIR = os.path.join(ROOT_DIR, '.poetry')

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


@dataclass
class Project:
    name: str

    def __repr__(self):
        return f'Project({self.name})'

    def export_requirements(self):
        os.chdir(self.repo_path)
        os.makedirs(self.poetry_path, exist_ok=True)
        run(f'poetry export -f requirements.txt > {self.requirements_path}')

    def archive(self):
        os.chdir(ROOT_DIR)
        run(f'tar cfvz {self.archive_file_path} {self.repo_path}')

    @property
    def repo_path(self):
        return os.path.join(PROJECTS_DIR, self.name)

    @property
    def poetry_path(self):
        return os.path.join(POETRY_DIR, self.name)

    @property
    def requirements_path(self):
        return os.path.join(self.poetry_path, 'requirements.txt')

    @property
    def archive_file_path(self):
        return os.path.join(ARCHIVE_DIR, f'{self.name}.tar.gz')


class DeployUtil:
    SET_PROJECTS, SET_MODE = ('projects', 'mode')
    MODE_CHOICES = (MODE_BUILD, MODE_RUN, MODE_BASH) = (
        'Build Docker Image',
        'Run Docker container',
        'Run Bash shell in Docker container',
    )
    ENABLE_PROJECTS_INFO_TXT_PATH = os.path.join(ROOT_DIR, 'projects.txt')

    def __init__(self):
        self.projects = []
        self.mode = None

    def deploy(self):
        self.pre_deploy()
        self.config()
        self.export_projects()

    def pre_deploy(self):
        def _make_dirs():
            os.chdir(ROOT_DIR)
            os.makedirs(POETRY_DIR, exist_ok=True)
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            Path(self.ENABLE_PROJECTS_INFO_TXT_PATH).touch()

        _make_dirs()

    def config(self):
        questions = []

        # Projects Questions
        cur_projects = sorted(os.listdir(PROJECTS_DIR))
        try:
            saved_projects_info = json.load(open(self.ENABLE_PROJECTS_INFO_TXT_PATH, 'rt'))
        except JSONDecodeError:
            saved_projects_info = json.loads('{}')

        for cur_project in cur_projects:
            saved_projects_info.setdefault(cur_project, True)
        questions.append({'type': 'checkbox', 'message': 'Select projects', 'name': self.SET_PROJECTS, 'choices': [
            {'name': name, 'checked': status} for name, status in saved_projects_info.items()
        ]})

        # Mode Questions
        questions.append({'type': 'list', 'message': 'Select mode', 'name': self.SET_MODE, 'choices': self.MODE_CHOICES})

        answers = prompt(questions)

        # Set & Save projects config
        for project in saved_projects_info:
            saved_projects_info[project] = project in answers[self.SET_PROJECTS]
        json.dump(saved_projects_info, open(self.ENABLE_PROJECTS_INFO_TXT_PATH, 'wt'))
        self.projects = [Project(name) for name, status in saved_projects_info.items() if status is True]

        # Set mode
        self.mode = answers[self.SET_MODE]

    def export_projects(self):
        print('Export projects requirements & archive')
        for index, project in enumerate(self.projects, start=1):
            project.export_requirements()
            project.archive()
            print(f' {index}. {project.name} ({project.requirements_path})')


if __name__ == '__main__':
    util = DeployUtil()
    util.deploy()
