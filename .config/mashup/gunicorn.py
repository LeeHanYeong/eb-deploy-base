daemon = False
chdir = '/srv/mashup/app'
bind = 'unix:/tmp/mashup.sock'
workers = 2
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/mashup.log'
errorlog = '/var/log/gunicorn/mashup-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/envs/env-mashup'
