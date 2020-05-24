daemon = False
chdir = '/srv/fc-headhunting/app'
bind = 'unix:/tmp/fc-headhunting.sock'
workers = 2
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/fc-headhunting.log'
errorlog = '/var/log/gunicorn/fc-headhunting-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/envs/env-fc-headhunting'
