from .base import *

DEBUG = True
AWS_SECRETS_MANAGER_SECRETS_SECTION = 'eb-deploy-base:dev'
ALLOWED_HOSTS += ['*']
WSGI_APPLICATION = 'config.wsgi.dev.application'
