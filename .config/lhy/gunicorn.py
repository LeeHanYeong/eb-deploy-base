daemon = False
chdir = '/srv/lhy/app'
bind = 'unix:/tmp/lhy.sock'
workers = 1
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/lhy.log'
errorlog = '/var/log/gunicorn/lhy-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/envs/env-lhy'
