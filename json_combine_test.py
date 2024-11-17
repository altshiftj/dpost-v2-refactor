import json
import os
import re
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def combine_json_files(folder_path):
    """
    Combines JSON files in the specified folder into separate combined files.
    A file is treated as the base if it lacks a '_number' suffix at the end.
    Related files sharing the same base are grouped together.
    
    Args:
        folder_path (str): The path to the folder containing JSON files.
    
    Returns:
        list: List of paths to the combined JSON files.
    """
    try:
        # List all JSON files in the folder
        json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        json_files.sort()  # Ensure consistent ordering

        if not json_files:
            logging.error("No JSON files found in the specified folder.")
            raise ValueError("No JSON files found in the specified folder.")

        # Regex to detect '_number' suffix at the end of the filename (1 or 2 digits)
        suffix_pattern = re.compile(r'_(\d{1,2})\.json$')

        # Group files by base name
        grouped_files = defaultdict(list)
        for file in json_files:
            # Check if the file has a '_number' suffix
            match = suffix_pattern.search(file)
            if match:
                # If suffix exists, derive the base name by removing '_number'
                base_name = file[:match.start()]
            else:
                # If no suffix, treat the file as the base
                base_name = file.replace('.json', '')
            
            grouped_files[base_name].append(file)

        combined_files = []

        # Process each group
        for base_name, files in grouped_files.items():
            combined_data = []
            for file in files:
                file_path = os.path.join(folder_path, file)
                try:
                    with open(file_path, 'r') as f:
                        file_data = json.load(f)
                        combined_data.append([file_data])  # Wrap each file's data in a list
                        logging.info(f"Successfully read file: {file}")
                except (json.JSONDecodeError, OSError) as e:
                    logging.error(f"Error reading or parsing file '{file}': {e}")
                    continue  # Skip the problematic file and proceed

            # Skip creating a combined file if no valid data
            if not combined_data:
                logging.warning(f"No valid data to combine for base name '{base_name}'. Skipping.")
                continue

            # Create a combined file for this group
            output_file = os.path.join(folder_path, f"{base_name}_combined.json")
            try:
                with open(output_file, 'w') as f:
                    json.dump(combined_data, f, indent=4)
                logging.info(f"Combined data for base '{base_name}' saved to {output_file}")
                combined_files.append(output_file)
            except OSError as e:
                logging.error(f"Error writing combined file '{output_file}': {e}")

        return combined_files

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        raise


if __name__ == "__main__":
    folder_path = r"test_monitor"
    combined_files = combine_json_files(folder_path)
    if combined_files:
        logging.info(f"Combined {len(combined_files)} JSON files. Files saved to: {combined_files}")
    else:
        logging.warning("No valid JSON files were combined.")