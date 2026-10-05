import os
import time
from config.settings import BRONZE_DIR, SILVER_DIR

# Configurable retention period in hours
FILE_RETENTION_HOURS = 24

def cleanup_old_files():
    """Deletes Bronze and Silver JSON and CSV files older than a specified retention period to conserve disk space.

    This function iterates through the Medallion architecture directories, identifies
    files exceeding the retention threshold based on their last modification time,
    and removes them to ensure the containerised environment remains efficient.

    Returns:
        None.
    """
    print("Starting automated garbage collection...")
    now = time.time()
    deleted_count = 0
    retention_seconds = FILE_RETENTION_HOURS * 3600
    
    for directory in [BRONZE_DIR, SILVER_DIR]:
        if not os.path.exists(directory):
            continue
            
        for root, _, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)
                
                # Verify the path is a file and targets specific data extensions
                if os.path.isfile(filepath) and (file.endswith(".json") or file.endswith(".csv")):
                    
                    # If the file exceeds the retention period, execute deletion
                    if os.stat(filepath).st_mtime < now - retention_seconds:
                        os.remove(filepath)
                        deleted_count += 1
                        
    print(f"Cleanup operation complete. Deleted {deleted_count} old files to free up space.")