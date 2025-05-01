from django.apps import AppConfig
import os

class PmjayFraudDashboardAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pmjay_fraud_dashboard_app'

    def ready(self):
        if not os.environ.get('RUN_MAIN'):
            return
        from apscheduler.schedulers.background import BackgroundScheduler
        from django.conf import settings
        from django.core.management import call_command

        scheduler = BackgroundScheduler()
        # Schedule every 10 minutes
        scheduler.add_job(
            call_command,
            'interval',
            minutes=10,
            args=['process_new_files'],
            id='process_new_files_job'
        )
        scheduler.start()