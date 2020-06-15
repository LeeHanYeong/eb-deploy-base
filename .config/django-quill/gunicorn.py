daemon = False
chdir = '/srv/django-quill/app'
bind = 'unix:/tmp/django-quill.sock'
workers = 2
threads = 1
timeout = 60
accesslog = '/var/log/gunicorn/django-quill.log'
errorlog = '/var/log/gunicorn/django-quill-error.log'
capture_output = True
raw_env = [
    'DJANGO_SETTINGS_MODULE=config.settings.production',
]
pythonpath = '/srv/envs/env-django-quill'
