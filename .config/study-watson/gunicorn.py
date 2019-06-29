daemon = False
chdir = '/srv/study-watson/app'
bind = 'unix:/tmp/study-watson.sock'
workers = 2
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/study-watson.log'
errorlog = '/var/log/gunicorn/study-watson-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/env-study-watson'
