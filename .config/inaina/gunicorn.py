daemon = False
chdir = '/srv/inaina/app'
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
pythonpath = '/srv/envs/env-inaina'
