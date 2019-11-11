FROM        python:3.7-slim
ENV         LANG C.UTF-8

# AWS Secrets
ARG         AWS_SECRETS_MANAGER_ACCESS_KEY_ID
ARG         AWS_SECRETS_MANAGER_SECRET_ACCESS_KEY
ENV         AWS_SECRETS_MANAGER_ACCESS_KEY_ID=$AWS_SECRETS_MANAGER_ACCESS_KEY_ID
ENV         AWS_SECRETS_MANAGER_SECRET_ACCESS_KEY=$AWS_SECRETS_MANAGER_SECRET_ACCESS_KEY

# eb-deploy packages & directories
RUN         apt -y update &&\
            apt -y dist-upgrade &&\
            apt -y install gcc nginx procps htop net-tools && \
            apt -y autoremove
RUN         mkdir /var/log/gunicorn

# eb-deploy requirements
COPY        requirements.txt           /tmp/requirements.txt
RUN         pip3 install -r /tmp/requirements.txt

# Projects venvs, install
RUN         mkdir /srv/project
WORKDIR     /srv/project
COPY        .poetry                 /srv/project/.poetry
COPY        container.py            /srv/project/
RUN         ./container.py --install

# Unarchive projects
COPY        . /srv/project
RUN         python3 /srv/project/container.py --unarchive

# Nginx config
RUN         rm -rf  /etc/nginx/sites-available/* &&\
            rm -rf  /etc/nginx/sites-enabled/* &&\
            cp -a   /srv/project/.config/nginx*.conf \
                    /etc/nginx/conf.d/
RUN         python3 /srv/project/container.py --nginx
RUN         python3 /srv/project/container.py --supervisor

# Django command, supervisord
CMD         python3 /srv/project/container.py --command && supervisord -c /srv/project/.config/supervisord.conf -n
EXPOSE      80
