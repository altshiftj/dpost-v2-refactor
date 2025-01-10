import os

def compile_codebase(source_dir, output_file, extensions=None):
    """
    Compiles all code files from the source directory into a single output file.

    Parameters:
    - source_dir (str): The root directory of your codebase.
    - output_file (str): The path to the output file where all code will be compiled.
    - extensions (list, optional): List of file extensions to include. Defaults to common code file extensions.
    """
    if extensions is None:
        # Define common code file extensions
        extensions = [
            '.py'
        ]

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_ext = os.path.splitext(file)[1]
                if file_ext.lower() in extensions:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            # if the file is empty, skip it
                            if os.stat(file_path).st_size == 0:
                                print(f'Skipped empty file: {file_path}')
                                continue
                            content = infile.read()
                            # remove any docstrings
                            content = '\n'.join([line for line in content.split('\n') if not line.strip().startswith('"""')])
                        
                        # Write a header for each file
                        outfile.write(f'\n\n# ======= {file_path} =======\n')
                        outfile.write(content)
                        outfile.write('\n# ======= End of {0} =======\n'.format(file_path))
                        print(f'Added: {file_path}')
                    except Exception as e:
                        print(f'Failed to read {file_path}: {e}')

    print(f'\nAll code has been compiled into {output_file}')

if __name__ == "__main__":
    source_directory = r'D:\Repos\ipat_data_watchdog\src'  # Replace with your codebase directory
    output_script = 'compiled_code.py'          # Replace with your desired output file name

    compile_codebase(source_directory, output_script)