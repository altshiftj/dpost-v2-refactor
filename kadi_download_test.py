from kadi_apy import KadiManager
import os

record_name = "sem_1_1_1_2024-11-29"
file_path = "SEM_1_1_1_2024-11-29_metadata.json"
file_id = "b9b76009-6021-46a2-9784-2d500b5542cf"

with KadiManager() as manager:
    record = manager.record(identifier=record_name)
    file_id = record.get_file_id(file_name=file_path)
    archive = record.download_file(file_id=file_id, file_path=file_path)
    print(archive)
