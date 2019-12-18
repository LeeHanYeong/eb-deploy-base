#!/usr/bin/env python
import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from time import sleep

import boto3
from PyInquirer import prompt

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true')
parser.add_argument('--run', action='store_true')
parser.add_argument('--bash', action='store_true')
parser.add_argument('--ci', action='store_true')
args = parser.parse_args()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(ROOT_DIR, 'projects')
ARCHIVE_DIR = os.path.join(ROOT_DIR, '.archive')
POETRY_DIR = os.path.join(ROOT_DIR, '.poetry')

AWS_PROFILE_SECRETS = 'lhy-secrets-manager'
AWS_PROFILE_EB = 'eb-deploy-base'
AWS_REGION = 'ap-northeast-2'

try:
    # 환경변수에서 Session세팅
    eb_access_key = os.environ['AWS_ACCESS_KEY_ID']
    eb_secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
    sm_access_key = os.environ['AWS_SECRETS_MANAGER_ACCESS_KEY_ID']
    sm_secret_key = os.environ['AWS_SECRETS_MANAGER_SECRET_ACCESS_KEY']
    SESSION_EB = boto3.Session(
        aws_access_key_id=eb_access_key,
        aws_secret_access_key=eb_secret_key,
        region_name=AWS_REGION,
    )
    SESSION_SECRETS = boto3.session.Session(
        aws_access_key_id=sm_access_key,
        aws_secret_access_key=sm_secret_key,
        region_name=AWS_REGION
    )
except KeyError:
    # 환경변수에 없는 경우(local), ~/.aws/credentials의 profile_name사용
    SESSION_SECRETS = boto3.session.Session(profile_name=AWS_PROFILE_SECRETS, region_name=AWS_REGION)
    SESSION_EB = boto3.session.Session(profile_name=AWS_PROFILE_EB, region_name=AWS_REGION)

SESSION_SECRETS_CREDENTIALS = SESSION_SECRETS.get_credentials()
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
        os.chdir(PROJECTS_DIR)
        run(f'tar cfvz {self.archive_file_path} {self.name}')

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

    @property
    def deploy_venv_path(self):
        return os.path.join(os.sep, 'srv', f'env-{self.name}')

    @property
    def deploy_python_path(self):
        return os.path.join(self.deploy_venv_path, 'bin', 'python3')

    @property
    def deploy_project_path(self):
        return os.path.join(os.sep, 'srv', self.name)

    @property
    def deploy_project_manage_path(self):
        return os.path.join(self.deploy_project_path, 'app', 'manage.py')


class AWSUtil:
    CNAME_PREFIX = 'eb-deploy-base.'
    ENV_NAME_GREEN = 'eb-deploy-base-green'
    ENV_NAME_BLUE = 'eb-deploy-base-blue'

    def __init__(self):
        self.is_first = False
        self.swap_cname = 'eb-deploy-base-swap'
        self.eb_client = boto3.client('elasticbeanstalk', region_name=AWS_REGION)
        self.elb_client = boto3.client('elbv2', region_name=AWS_REGION)
        self.ec2_client = boto3.client('ec2', region_name=AWS_REGION)
        self.sm_client = SESSION_SECRETS.client('secretsmanager', region_name=AWS_REGION)
        self.acm_arn = json.loads(
            self.sm_client.get_secret_value(
                SecretId='lhy'
            )['SecretString'])['eb-deploy-base']['base']['AWS_ACM_ARN']
        self.running_environment = None
        self.running_environment_name = None
        self.swap_environment_name = None

    def _get_running_environment(self):
        """
        실행중인 Environment가져오기
        """
        if self.running_environment is None:
            environments = [
                environment for environment in self.eb_client.describe_environments()['Environments']
                if environment['Status'] != 'Terminated'
            ]
            if len(environments) == 0:
                self.is_first = True
                self.swap_cname = 'eb-deploy-base'
                self.running_environment = {'EnvironmentName': self.ENV_NAME_BLUE}
            elif len(environments) != 1:
                raise Exception(f'실행중인 환경이 1개가 아닙니다 (총 {len(environments)}개)')
            else:
                self.running_environment = environments[0]
        return self.running_environment

    def _get_environment_names(self):
        self.running_environment_name = self._get_running_environment()['EnvironmentName']
        if self.running_environment_name == self.ENV_NAME_BLUE:
            self.swap_environment_name = self.ENV_NAME_GREEN
        else:
            self.swap_environment_name = self.ENV_NAME_BLUE

    def _eb_create(self, sample=False, staged=False):
        env_vars = ','.join(
            f'{key}={value}' for key, value in {
                'AWS_SECRETS_MANAGER_ACCESS_KEY_ID': SECRETS_MANAGER_ACCESS_KEY,
                'AWS_SECRETS_MANAGER_SECRET_ACCESS_KEY': SECRETS_MANAGER_SECRET_KEY,
            }.items())
        run(f'eb create {self.swap_environment_name} '
            f'--cname {self.swap_cname} '
            f'--elb-type application '
            f'--envvars {env_vars}'
            f'{" --sample" if sample else ""}')

        # eb deploy
        if sample:
            run('git add -A')
            run(f'eb deploy '
                f'{"--staged " if staged else ""}'
                f'--timeout 20 '
                f'{self.swap_environment_name}')
            run('git reset HEAD', stdout=subprocess.DEVNULL)

    def _eb_settings(self):
        # 새로 생성한 Environment의 LoadBalancer
        swap_load_balancer = self.eb_client.describe_environment_resources(
            EnvironmentName=self.swap_environment_name
        )['EnvironmentResources']['LoadBalancers'][0]

        # 새로 생성한 LoadBalancer의 TargetGroup
        swap_target_group = self.elb_client.describe_target_groups(
            LoadBalancerArn=swap_load_balancer['Name'],
        )['TargetGroups'][0]['TargetGroupArn']

        # 새로 생성한 LoadBalancer의 SecurityGroup
        swap_security_group_id = self.elb_client.describe_load_balancers(
            LoadBalancerArns=[swap_load_balancer['Name']]
        )['LoadBalancers'][0]['SecurityGroups'][0]

        # 새 LoadBalancer에 HTTPS Listener추가 및 ACM추가
        self.elb_client.create_listener(
            LoadBalancerArn=swap_load_balancer['Name'],
            Protocol='HTTPS',
            Port=443,
            Certificates=[
                {
                    'CertificateArn': self.acm_arn,
                },
            ],
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': swap_target_group,
                }
            ]
        )

        # 새 LoadBalancer의 securityGroup에 443Port Inbound추가
        self.ec2_client.authorize_security_group_ingress(
            GroupId=swap_security_group_id,
            IpPermissions=[
                {
                    'FromPort': 443,
                    'IpProtocol': 'tcp',
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                    'Ipv6Ranges': [{'CidrIpv6': '::/0'}],
                    'ToPort': 443,
                }
            ]
        )

    def _eb_swap(self):
        # CName Swap
        self.eb_client.swap_environment_cnames(
            SourceEnvironmentName=self.running_environment_name,
            DestinationEnvironmentName=self.swap_environment_name,
        )

        # 새 Environment의 CNAME이 CNAME_PREFIX로 시작할때까지 기다림
        while True:
            cname = self.eb_client.describe_environments(
                EnvironmentNames=[self.swap_environment_name],
            )['Environments'][0]['CNAME']
            sleep(5)
            if self.CNAME_PREFIX in cname:
                break

        # 기존 Environment terminate
        self.eb_client.terminate_environment(
            EnvironmentName=self.running_environment_name,
        )

    def deploy(self):
        print('AWS Deploy Start')
        self._get_running_environment()
        self._get_environment_names()
        print(' - eb create')
        self._eb_create()
        print(' - eb settings')
        self._eb_settings()
        if not self.is_first:
            print(' - eb swap')
            self._eb_swap()
        print('AWS Deploy Finished')


class DeployUtil:
    SET_PROJECTS, SET_MODE = ('projects', 'mode')
    MODE_CHOICES = (MODE_BUILD, MODE_RUN, MODE_BASH, MODE_DEPLOY) = (
        'Build Docker Image',
        'Run Docker container',
        'Run Bash shell in Docker container',
        'EB Deploy',
    )
    ENABLE_PROJECTS_INFO_TXT_PATH = os.path.join(ROOT_DIR, 'projects.txt')

    def __init__(self, ci=False):
        self.projects = []
        self.mode = None
        self.ci = ci

    def deploy(self):
        self.pre_deploy()
        self.config()
        self.export_requirements()
        self.export_projects()

        self.docker_build()
        if self.mode == self.MODE_BUILD:
            return
        if self.mode == self.MODE_RUN:
            self.docker_run()
        elif self.mode == self.MODE_BASH:
            self.docker_bash()
        elif self.mode == self.MODE_DEPLOY:
            self.push_ecr()
            self.eb_deploy()

    def pre_deploy(self):
        def _remove_exists_dirs():
            os.chdir(ROOT_DIR)
            shutil.rmtree(POETRY_DIR, ignore_errors=True)
            shutil.rmtree(ARCHIVE_DIR, ignore_errors=True)

        def _make_dirs():
            os.chdir(ROOT_DIR)
            os.makedirs(POETRY_DIR, exist_ok=True)
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            Path(self.ENABLE_PROJECTS_INFO_TXT_PATH).touch()

        _remove_exists_dirs()
        _make_dirs()

    def config(self):
        # CI모드일 경우, 전체 배포
        if self.ci:
            self.projects = [Project(name) for name in sorted(os.listdir(PROJECTS_DIR))]
            self.mode = self.MODE_DEPLOY
            return

        # Projects Questions
        questions = []
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
        questions.append(
            {'type': 'list', 'message': 'Select mode', 'name': self.SET_MODE, 'choices': self.MODE_CHOICES})

        answers = prompt(questions)

        # Set & Save projects config
        for project in saved_projects_info:
            saved_projects_info[project] = project in answers[self.SET_PROJECTS]
        json.dump(saved_projects_info, open(self.ENABLE_PROJECTS_INFO_TXT_PATH, 'wt'))
        self.projects = [Project(name) for name, status in saved_projects_info.items() if status is True]

        # Set mode
        self.mode = answers[self.SET_MODE]

    @staticmethod
    def export_requirements():
        os.chdir(ROOT_DIR)
        run(f'poetry export -f requirements.txt > requirements.txt')

    def export_projects(self):
        print('Export projects requirements & archive')
        for index, project in enumerate(self.projects, start=1):
            project.export_requirements()
            project.archive()
            print(f' {index}. {project.name} ({project.requirements_path})')

    @staticmethod
    def docker_build():
        os.chdir(ROOT_DIR)
        run('docker pull python:3.7-slim')
        run('docker build {build_args} -t {tag} -f {dockerfile} .'.format(
            build_args=' '.join([
                f'--build-arg {key}={value}'
                for key, value in {
                    'AWS_ACCESS_KEY_ID': EB_ACCESS_KEY,
                    'AWS_SECRET_ACCESS_KEY': EB_SECRET_KEY,
                    'AWS_SECRETS_MANAGER_ACCESS_KEY_ID': SECRETS_MANAGER_ACCESS_KEY,
                    'AWS_SECRETS_MANAGER_SECRET_ACCESS_KEY': SECRETS_MANAGER_SECRET_KEY,
                }.items()
            ]),
            tag=IMAGE_PRODUCTION_LOCAL,
            dockerfile='Dockerfile.local',
        ))

    @staticmethod
    def docker_run():
        run(f'{RUN_CMD}')

    @staticmethod
    def docker_bash():
        run(f'{RUN_CMD} /bin/bash')

    @staticmethod
    def push_ecr():
        # Push ECR
        run(f'docker tag {IMAGE_PRODUCTION_LOCAL} {IMAGE_PRODUCTION_ECR}')
        run(f'$(aws ecr get-login --no-include-email --region ap-northeast-2) && docker push {IMAGE_PRODUCTION_ECR}')

    @staticmethod
    def eb_deploy():
        AWSUtil().deploy()


if __name__ == '__main__':
    util = DeployUtil(ci=args.ci)
    util.deploy()
