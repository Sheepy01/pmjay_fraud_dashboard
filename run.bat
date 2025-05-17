@echo off
cd /d "%~dp0"

@REM echo Processing existing files...
@REM python manage.py process_new_files
@REM python manage.py import_data

echo Starting Django server...
start cmd /k "python manage.py runserver"

timeout /t 5 /nobreak >nul

@REM echo Starting scheduler...
@REM start cmd /k "python manage.py scheduler"

echo System ready! Access dashboard at http://localhost:8000
exit