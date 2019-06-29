daemon = False
chdir = '/srv/fitcha/app'
bind = 'unix:/tmp/fitcha.sock'
workers = 2
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/fitcha.log'
errorlog = '/var/log/gunicorn/fitcha-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/env-fitcha'
