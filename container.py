#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--install', action='store_true')
parser.add_argument('--unarchive', action='store_true')
parser.add_argument('--nginx', action='store_true')
parser.add_argument('--supervisor', action='store_true')
parser.add_argument('--command', action='store_true')
parser.add_argument('--db', action='store_true')
args = parser.parse_args()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(ROOT_DIR, '.config')
PROJECTS_DIR = os.path.join(ROOT_DIR, 'projects')
ARCHIVE_DIR = os.path.join(ROOT_DIR, '.archive')
POETRY_DIR = os.path.join(ROOT_DIR, '.poetry')


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, **kwargs)


def install():
    os.chdir(ROOT_DIR)
    for project in os.listdir(POETRY_DIR):
        run(f'python3 -m venv /srv/env-{project}')
        run(f'/srv/env-{project}/bin/pip3 install'
            f' -r /srv/project/.poetry/{project}/requirements.txt')


def unarchive():
    os.chdir(ROOT_DIR)
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    for project in os.listdir(POETRY_DIR):
        run(f'tar -xzvf .archive/{project}.tar.gz -C /srv')


def nginx():
    os.chdir(ROOT_DIR)
    for project in os.listdir(POETRY_DIR):
        shutil.copy(os.path.join(CONFIG_DIR, project, f'nginx.{project}.conf'), '/etc/nginx/conf.d/')


def supervisor():
    os.chdir(ROOT_DIR)
    with open(os.path.join(CONFIG_DIR, 'supervisord.conf'), 'at') as f:
        for project in os.listdir(POETRY_DIR):
            f.write('\n')
            f.write(f'[program:{project}]\n')
            f.write(f'command=/srv/env-{project}/bin/gunicorn -c '
                    f'/srv/project/.config/{project}/gunicorn.py '
                    f'config.wsgi.production:application\n')


def execute_django_commands():
    os.chdir(ROOT_DIR)
    for project in os.listdir(POETRY_DIR):
        env = 'DJANGO_SETTINGS_MODULE=config.settings.production'
        python = f'/srv/env-{project}/bin/python3'
        manage = f'/srv/{project}/app/manage.py'
        run(f'{env} {python} {manage} collectstatic --noinput')
        run(f'{env} {python} {manage} migrate --noinput')


def db_backup():
    os.chdir(ROOT_DIR)
    for project in os.listdir(POETRY_DIR):
        env = 'DJANGO_SETTINGS_MODULE=config.settings.production'
        python = f'/srv/env-{project}/bin/python3'
        manage = f'/srv/{project}/app/manage.py'
        run(f'{env} {python} {manage} dbbackup')


if __name__ == '__main__':
    if args.install:
        install()
        exit(0)

    if args.unarchive:
        unarchive()
        exit(0)

    if args.nginx:
        nginx()
        exit(0)

    if args.supervisor:
        supervisor()
        exit(0)

    if args.command:
        execute_django_commands()
        exit(0)

    if args.db:
        db_backup()
        exit(0)
