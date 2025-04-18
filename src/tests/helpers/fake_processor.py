from processing.file_processor_abstract import FileProcessorABS

class DummyProcessor(FileProcessorABS):
    def device_specific_preprocessing(self, src_path: str) -> str:
        # Pretend to sanitize the path
        return src_path

    def is_valid_datatype(self, path: str) -> bool:
        # All files are accepted
        return True

    def is_appendable(self, record, filename_prefix: str, extension: str) -> bool:
        # Always allow appending
        return True

    def device_specific_processing(self, src_path: str, record_path: str, file_id: str, extension: str):
        # Return a fake destination path and datatype
        dummy_final_path = f"{record_path}/dummy_file{extension}"
        return dummy_final_path, "dummy_type"
