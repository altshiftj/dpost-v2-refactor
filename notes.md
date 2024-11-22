### 11/17/2024
Current issues/improvements to keep in mind:
- file_watchdog.py 
    - needs to maintain and check a flat dictionary db for files that have already been processed.
        - it should ascertain whether the incoming file is part of a new record, or an update to an existing record.
        - user should be prompted to confirm the update. if it is not an update to a previous record, the user should be forced to rename the file.
    - change naming convention that needs to be followed
    - change the way the filename is cleansed
    - warn the user of characters that are not allowed in the filename, especially in particular tokens of the filename.

- metadata_watchdog.py
    - should generate a single flat dictionary for each file it processes which is sent to the kadidb and owned administratively by the device owner.
        - the dictionary should contain each each file's metadata, and the file's hash.
        - this is *not* the dictionary that file_watchdog.py will check to see if a file has already been processed.

- session_watchdog.py
    - remove dictionary conversion code, leave this to metadata_watchdog.py...?

- General:
    - upload the aggregated metadata dictionary to the kadidb as a separate file, rather than extra metadata.
    - consider if there are any metadata values that should be added as extra metadata.
    - improve readability of tkinter GUIs.
    - add functionality for .elid folders

- Important functionality before I-Sem:
    - none?
    - what to talk about then...?
        - the watchdog concept, a timeframe for the project, and the current state of the project.
        - going forward and backward in data processing (historical data).
        - the importance of metadata in the project.
        - overall concept of linking everything (Horiba to SEM for example)
        - asking for device users/owners to contribute with knowledge of their devices.
        - MYData campaign
            - mind your data

- Lots of functionality after fullWatchdog implementation, now consider:
    - metadata archive and looking at what records exist already
    - updating records if new files arrive in a new session
    - extras that might be valuable to include in sync. PERHAPS DONT EVEN THINK ABOUT IT
    - elid folders. not surface profile folders yet
    - name cleansing and policing
    - project cleanup
    - asking user if they want to update a record if a file is already in the db, or if they want to create a new record, prompting for a new name.
    - granting data access to the device users by extracting user name from the file name.
