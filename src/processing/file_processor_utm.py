from src.processing.file_processor_abstract import FileProcessorBase
from src.records.local_record import LocalRecord


class FileProcessorUTM(FileProcessorBase):
    """
    File processor for UTM (Universal Test Machine) files.
    Inherits from BaseFileProcessor and implements methods specific to UTM files.
    """

    def device_specific_preprocessing(self, src_path: str) -> str:
        """
        Method to implement optional preprocessing steps before routing the item.
        """
        pass

    def is_valid_datatype(self, path: str):
        """
        Checks if the file/folder at the given path is valid for this processor.
        Returns (bool|None) -> (is_valid, data_type).
        """
        pass

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        """
        Checks if the record can be appended to with this processor's data type.
        Return: (appendable, message_if_not_appendable)
        """
        pass

    def device_specific_processing(self, source_path, record_path, file_id, extension):
        """
        Allows subclasses to implement custom moves, renames, or metadata extraction.
        Must return the final path of the processed item.
        """
        pass
