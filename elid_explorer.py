from rsciio import phenom
import imagecodecs
import json
import re

file_path = r'D:\Repos\ipat_data_watchdog\test_elid\test.elid'

def load_elid_file(file_path: str) -> None:
    '''
    Loads the ELID file and returns the data as a DataFrame
    '''
    # Load the ELID file
    elid_file = phenom.file_reader(file_path)

    return elid_file

def extract_elid_metadata(elid_file: dict) -> dict:
    '''
    Extracts the metadata from the ELID file
    '''
    # Patterns
    image_pattern = r"^Image \d+$"
    analysis_pattern = r"^Image \d+, (Spot|Line|Region|Map) \d+$"

    for i in elid_file.len():
        if not re.match(image_pattern, elid_file[i]['metadata']['General']['title']):
            print(i)

    return metadata

if __name__ == '__main__':
    elid = load_elid_file(file_path)


