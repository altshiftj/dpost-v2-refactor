from rsciio import phenom
import imagecodecs
import json

file_path = r'D:\Repos\ipat_data_watchdog\test_elid\test.elid'

def load_elid_file(file_path: str) -> None:
    '''
    Loads the ELID file and returns the data as a DataFrame
    '''
    # Load the ELID file
    elid_file = phenom.file_reader(file_path)

    return elid_file

if __name__ == '__main__':
    elid = load_elid_file(file_path)

    # save the elid dictionary to a json file
    with open('elid.json', 'w') as f:
        json.dump(elid, f)

