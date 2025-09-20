import os

# Get env var. : local/production

def get_secret(key, default=None):
    return os.getenv(key, default)

pipeline = get_secret('PIPELINE')

if pipeline == 'PRODUCTION':
    from .production import *
else:
    from .local import *
