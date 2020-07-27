daemon = False
bind = 'unix:/tmp/inaina.sock'
workers = 1
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/inaina.log'
errorlog = '/var/log/gunicorn/inaina-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]

chdir = '/srv/inaina/app'
pythonpath = '/srv/envs/env-inaina/lib/python3.8/site-packages'
