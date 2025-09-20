from pathlib import Path
from .base import *

# Default secret key for production
SECRET_KEY = 'django-insecure-kyhp0p)_^nhjk)8l%bg1q-mfr#6bbkoaesf9cz@c6hqpuup_8k'

DEBUG = True

SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY
