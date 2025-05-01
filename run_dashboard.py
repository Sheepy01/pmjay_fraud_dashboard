#!/usr/bin/env python
import os
import sys
from pathlib import Path
from django.core.management import execute_from_command_line
import whitenoise
import whitenoise.middleware
import whitenoise.storage
import whitenoise.runserver_nostatic

# ─── Redirect stdout/stderr if running without console ─────────────
if os.name == 'nt' and not sys.stdout:
    devnull = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
    sys.stdout = devnull
    sys.stderr = devnull

# ─── Point Django at your settings ─────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmjay_fraud_dashboard.settings')

# ─── Base directory (for data/, static/, etc.) ─────────────────────
BASE_DIR = Path(__file__).resolve().parent

def run_management_command(cmd_list):
    """Helper to invoke manage.py commands."""
    execute_from_command_line(['manage.py'] + cmd_list)

if __name__ == '__main__':
    # 1) Import your Excel data
    run_management_command(['import_data'])

    # 2) Collect static files into STATIC_ROOT
    run_management_command(['collectstatic', '--noinput'])

    # 3) Launch the Django server *without* autoreload
    run_management_command([
        'runserver',
        '0.0.0.0:8000',
        '--noreload',
    ])
