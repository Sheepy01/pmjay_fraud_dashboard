import time
import os
import glob
import shutil
from import_data import Command  # Assuming import_data is in the same directory

WATCH_FOLDER = 'data/new_files/'
PROCESSED_FOLDER = 'data/processed_files/'

def watch_for_files():
    print(f"Watching folder: {WATCH_FOLDER} for new Excel files...")

    while True:
        files = glob.glob(os.path.join(WATCH_FOLDER, 'Last 24 Hours Bihar Reports *.xlsx'))
        if files:
            for file in files:
                print(f"File detected: {file}")
                # Process the file and merge data
                process_file(file)
        else:
            print("No new files found, waiting...")

        time.sleep(10)  # Check for new files every 10 seconds

def process_file(file_path):
    # Trigger import_data command (make sure it's configured properly)
    command = Command()
    command.handle()  # Handle the command; this will import the data

    # Move file to processed folder
    if os.path.exists(file_path):
        shutil.move(file_path, os.path.join(PROCESSED_FOLDER, os.path.basename(file_path)))
        print(f"File moved to processed folder: {file_path}")

if __name__ == "__main__":
    watch_for_files()
