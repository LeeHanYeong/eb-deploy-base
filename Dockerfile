FROM        azelf/eb-deploy-base:base
COPY        . /srv/project
RUN         mkdir /var/log/gunicorn
RUN         python3 /srv/project/deploy.py --eb

RUN         rm -rf  /etc/nginx/sites-available/* &&\
            rm -rf  /etc/nginx/site-enabled/* &&\
            cp -a   /srv/project/.config/nginx*.conf \
                    /etc/nginx/conf.d/

CMD         supervisord -c /srv/project/.config/supervisord.conf -n
EXPOSE      80
