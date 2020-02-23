daemon = False
chdir = '/srv/washble/app'
bind = 'unix:/tmp/washble.sock'
workers = 1
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/washble.log'
errorlog = '/var/log/gunicorn/washble-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/envs/env-washble'
