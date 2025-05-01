from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime  # Correct import
import time

class Command(BaseCommand):
    help = 'Run scheduled tasks'

    def handle(self, *args, **options):
        scheduler = BlockingScheduler()
        
        def file_check_job():
            self.stdout.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running scheduled file check...")
            from django.core.management import call_command
            call_command('process_new_files')
            call_command('import_data')

        # Add first run immediately
        scheduler.add_job(
            file_check_job,
            trigger=IntervalTrigger(minutes=5),
            id='file_check',
            max_instances=1,
            next_run_time=datetime.now()  # Now works with correct import
        )

        try:
            self.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduler starting...")
            scheduler.start()
        except KeyboardInterrupt:
            scheduler.shutdown()