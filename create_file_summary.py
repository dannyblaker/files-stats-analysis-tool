import os
import csv
from collections import defaultdict
from statistics import median
import time
from tqdm import tqdm
from dotenv import load_dotenv

# exclude_dirs = {'node_modules', '.git', '__pycache__'}
exclude_dirs = {}
# exclude_extensions = {'.txt', '.png'}
exclude_extensions = {}

def file_size_mb(fsize):
    return fsize / (1024 * 1024)

def scan_directory(path):
    summary = defaultdict(list)
    for root, dirs, files in tqdm(os.walk(path)):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in files:
            if any(name.endswith(ext) for ext in exclude_extensions):
                continue
            full_path = os.path.join(root, name)
            if os.path.islink(full_path) and not os.path.exists(full_path):
                continue
            try:
                stats = os.stat(full_path)
            except FileNotFoundError:
                continue
            extension = os.path.splitext(name)[1]
            file_data = {
                'size': file_size_mb(stats.st_size),
                'last_accessed': stats.st_atime,
                'last_modified': stats.st_mtime,
                'created': stats.st_ctime,
                'owned_by_current_user': stats.st_uid == os.getuid(),
                'owned_by_root': stats.st_uid == 0,
            }
            summary[extension].append(file_data)
    return summary

def get_summary_data(summary):
    summary_data = []
    for extension, files in tqdm(summary.items()):
        total_files = len(files)
        total_size = sum(file['size'] for file in files)
        average_size = total_size / total_files
        median_size = median(file['size'] for file in files)
        file_sizes = [file['size'] for file in files]
        access_times = [file['last_accessed'] for file in files]
        modified_times = [file['last_modified'] for file in files]
        created_times = [file['created'] for file in files]
        owned_by_current_user = sum(file['owned_by_current_user'] for file in files)
        owned_by_root = sum(file['owned_by_root'] for file in files)
        data = [
            extension,
            total_files,
            total_size,
            round(average_size, 2),
            round(median_size, 2),
            round(percentage_of_files(file_sizes, 1), 2),
            round(percentage_of_files(file_sizes, 1, True), 2),
            round(percentage_of_files(file_sizes, 5, True), 2),
            round(percentage_of_files(file_sizes, 100, True), 2),
            round(percentage_of_files(file_sizes, 500, True), 2),
            round(percentage_of_files(file_sizes, 500), 2),
            round(percentage_of_files(access_times, time.time() - 24*60*60), 2),
            round(percentage_of_files(access_times, time.time() - 3*24*60*60), 2),
            round(percentage_of_files(access_times, time.time() - 7*24*60*60), 2),
            round(percentage_of_files(access_times, time.time() - 30*24*60*60), 2),
            round(percentage_of_files(access_times, time.time() - 90*24*60*60), 2),
            round(percentage_of_files(access_times, time.time() - 180*24*60*60), 2),
            round(percentage_of_files(access_times, time.time() - 365*24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 3*24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 7*24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 30*24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 90*24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 180*24*60*60), 2),
            round(percentage_of_files(modified_times, time.time() - 365*24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 3*24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 7*24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 30*24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 90*24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 180*24*60*60), 2),
            round(percentage_of_files(created_times, time.time() - 365*24*60*60), 2),
            round(owned_by_current_user / total_files * 100, 2),
            round(owned_by_root / total_files * 100, 2),
        ]
        summary_data.append(data)
    return summary_data

def percentage_of_files(values, threshold, less_than=False):
    if less_than:
        matches = [value for value in values if value < threshold]
    else:
        matches = [value for value in values if value >= threshold]
    return len(matches) / len(values) * 100

def write_to_csv(data, filename='summary.csv'):
    header = [
        'file_extension_type', 
        'total_number_files_found', 
        'total_file_size_mb', 
        'average_size_mb', 
        'median_size_mb', 
        'percent_above_1_mb', 
        'percent_below_1_mb_each', 
        'percent_below_5_mb_each', 
        'percent_below_100_mb_each', 
        'percent_below_500_mb_each', 
        'percent_above_or_equal_to_500_mb', 
        'percent_last_accessed_today', 
        'percent_last_accessed_last_3_days', 
        'percent_last_accessed_last_week', 
        'percent_last_accessed_last_month', 
        'percent_last_accessed_last_3_months', 
        'percent_last_accessed_last_6_months', 
        'percent_last_accessed_last_year', 
        'percent_last_modified_today', 
        'percent_last_modified_last_3_days', 
        'percent_last_modified_last_week', 
        'percent_last_modified_last_month', 
        'percent_last_modified_last_3_months', 
        'percent_last_modified_last_6_months', 
        'percent_last_modified_last_year', 
        'percent_created_today', 
        'percent_created_last_3_days', 
        'percent_created_last_week', 
        'percent_created_last_month', 
        'percent_created_last_3_months', 
        'percent_created_last_6_months', 
        'percent_created_last_year', 
        'percent_owned_by_current_user', 
        'percent_owned_by_root'
        ]
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for row in data:
            writer.writerow(row)

def main():
    load_dotenv()
    path = os.getenv("SCAN_PATH")
    if not path:
        raise ValueError("SCAN_PATH not set in .env file")
    summary = scan_directory(path)
    summary_data = get_summary_data(summary)
    write_to_csv(summary_data)

if __name__ == "__main__":
    main()
