from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS, ProcessingOutput


class DummyProcessor(FileProcessorABS):
    def __init__(self, valid_datatype=True, appendable=True):
        self.valid_datatype = valid_datatype
        self.appendable = appendable

    def device_specific_preprocessing(self, src_path: str) -> str:
        return src_path

    def is_appendable(self, record, filename_prefix: str, extension: str) -> bool:
        return self.appendable

    def device_specific_processing(self, src_path: str, record_path: str, file_id: str, extension: str) -> ProcessingOutput:
        dummy_final_path = f"{record_path}/dummy_file{extension}"
        return ProcessingOutput(dummy_final_path, "dummy_type")
