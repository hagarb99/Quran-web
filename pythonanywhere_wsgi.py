# +-------------------------------------------------------------------------+
# | PythonAnywhere WSGI configuration file for Quran Halaqat Platform       |
# +-------------------------------------------------------------------------+
# Copy this content into your PythonAnywhere WSGI configuration file:
# /var/www/<your-username>_pythonanywhere_com_wsgi.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. Project path on PythonAnywhere
# Ensure this matches your repository directory (e.g. /home/<your-username>/quran-app)
PROJECT_DIR = os.path.expanduser('~/quran-app')
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 2. Load .env environment variables
env_path = Path(PROJECT_DIR) / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 3. Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# 4. Activate Django WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

