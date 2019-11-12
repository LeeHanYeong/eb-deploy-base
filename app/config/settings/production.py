from .base import *

AWS_SECRETS_MANAGER_SECRETS_SECTION = 'eb-deploy-base:production'
ALLOWED_HOSTS += SECRETS['ALLOWED_HOSTS']
WSGI_APPLICATION = 'config.wsgi.production.application'
