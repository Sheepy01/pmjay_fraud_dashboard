import os
import shutil
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Process new files and merge into universal file'

    def handle(self, *args, **options):
        # Define paths
        BASE_DIR = settings.BASE_DIR
        NEW_FILES_DIR = os.path.join(BASE_DIR, 'data', 'new_files')
        PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed_files')
        UNIVERSAL_FILE = os.path.join(BASE_DIR, 'data', 'Combined_Last24Hours.xlsx')

        # Create directories if missing
        os.makedirs(NEW_FILES_DIR, exist_ok=True)
        os.makedirs(PROCESSED_DIR, exist_ok=True)

        # Process new files
        processed = 0
        for filename in os.listdir(NEW_FILES_DIR):
            # Split filename into base and extension
            base_name, file_ext = os.path.splitext(filename)
            file_ext = file_ext.lower()  # Normalize extension to lowercase
            
            # Check conditions (either name pattern OR Excel extension)
            if (
                base_name.startswith('Last 24 Hours Bihar Reports')  # Name condition
                or 
                file_ext in ['.xlsx', '.xls']  # Extension condition
            ):
                file_path = os.path.join(NEW_FILES_DIR, filename)
                try:
                    # Read files
                    new_data = pd.read_excel(file_path, sheet_name='Dump')
                    new_data.columns = new_data.columns.str.strip()
                    
                    if os.path.exists(UNIVERSAL_FILE):
                        existing_data = pd.read_excel(UNIVERSAL_FILE, sheet_name='Dump')
                        combined = pd.concat([existing_data, new_data], ignore_index=True)
                    else:
                        combined = new_data
                    
                    # Remove duplicates
                    combined = combined.drop_duplicates(
                        subset=['Registration Id', 'Case Id'],
                        keep='last'
                    )
                    
                    # Save universal file
                    combined.to_excel(UNIVERSAL_FILE, index=False, sheet_name='Dump')
                    
                    # Move processed file
                    shutil.move(file_path, os.path.join(PROCESSED_DIR, filename))
                    processed += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing {filename}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'Processed {processed} new files'))
        
        if processed > 0:
            self.stdout.write(self.style.SUCCESS('Refreshing database with new data...'))
            from django.core.management import call_command
            call_command('import_data')