from abc import ABC, abstractmethod
from ipat_watchdog.core.records.local_record import LocalRecord


class FileProcessorABS(ABC):
    """
    An abstract base for processors that handle new/modified files or directories
    and associate them with records in the system.
    """

    @abstractmethod
    def device_specific_preprocessing(self, src_path: str) -> str:
        """
        Method to implement optional preprocessing steps before routing the item.
        """
        pass

    @abstractmethod
    def is_valid_datatype(self, path: str):
        """
        Checks if the file/folder at the given path is valid for this processor.
        Returns (bool|None) -> (is_valid, data_type).
        """
        pass

    @abstractmethod
    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        """
        Checks if the record can be appended to with this processor's data type.
        Return: (appendable, message_if_not_appendable)
        """
        pass

    @abstractmethod
    def device_specific_processing(self, source_path, record_path, file_id, extension):
        """
        Allows subclasses to implement custom moves, renames, or metadata extraction.
        Must return the final path of the processed item.
        """
        pass

class FileProcessorBase(FileProcessorABS):
    """
    A base class for file processors that provides default implementations for
    some methods. Subclasses can override these methods as needed.
    """

    def device_specific_preprocessing(self, src_path: str) -> str:
        """
        Default implementation does nothing and returns the source path.
        """
        return src_path

    def is_valid_datatype(self, path: str):
        """
        Default implementation always returns None (no validation).
        """
        return None, None

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        """
        Default implementation always returns True (appendable).
        """
        return True, ""