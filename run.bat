@echo off
cd /d "%~dp0"

echo Processing existing files...
python manage.py process_new_files
python manage.py import_data

echo Starting Django server...
start cmd /k "python manage.py runserver"

timeout /t 5 /nobreak >nul

echo Starting scheduler...
start cmd /k "python manage.py scheduler"

echo System ready! Access dashboard at http://localhost:8000
exit