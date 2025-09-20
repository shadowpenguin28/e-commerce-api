from pathlib import Path
from .base import *

def get_secret(key, default=None):
    return os.getenv(key, default)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# # SET SECRET KEY MANUALLY 
# SECRET_KEY = ''

# Fetch Secret Key from Enviroment
SECRET_KEY = get_secret('SECRET_KEY')

DEBUG = False

SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

