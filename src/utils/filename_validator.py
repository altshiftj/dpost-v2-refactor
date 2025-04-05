from src.config.settings import FILENAME_PATTERN, ID_SEP
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class FilenameValidator:
    """
    Validates and sanitizes filename prefixes using the expected format:
    'UserID-Institute-Sample_ID'. Also supports validating structured dialog
    input (e.g., rename prompts).
    """

    @staticmethod
    def is_valid_prefix(raw_prefix: str) -> bool:
        """
        Validates prefix format using a regex and required separator count.

        Args:
            raw_prefix (str): The raw filename prefix to check.

        Returns:
            bool: True if valid, False otherwise.
        """
        if not FILENAME_PATTERN.match(raw_prefix):
            logger.debug(f"Prefix '{raw_prefix}' failed regex match.")
            return False
        return raw_prefix.count(ID_SEP) >= 2


    @staticmethod
    def sanitize_prefix(raw_prefix: str) -> str:
        """
        Sanitizes a raw filename prefix.

        - Lowercases user ID and institute
        - Replaces spaces with underscores in the sample ID

        Args:
            raw_prefix (str): The unsanitized filename prefix.

        Returns:
            str: A cleaned, standardized filename prefix.
        """
        parts = raw_prefix.strip().split(ID_SEP)
        if len(parts) < 3:
            return raw_prefix

        user_id = parts[0]
        institute = parts[1]
        sample_id = ID_SEP.join(parts[2:]).replace(' ', '_')

        return f"{user_id.lower()}{ID_SEP}{institute.lower()}{ID_SEP}{sample_id}"


    @classmethod
    def sanitize_and_validate(cls, raw_prefix: str) -> tuple[str, bool]:
        """
        Validates and sanitizes a filename prefix in one step.

        Args:
            raw_prefix (str): The filename prefix to validate and clean.

        Returns:
            tuple[str, bool]: (sanitized_name, is_valid)
        """
        if not cls.is_valid_prefix(raw_prefix):
            return raw_prefix, False
        return cls.sanitize_prefix(raw_prefix), True


    @classmethod
    def from_user_input(cls, dialog_result: dict | None) -> tuple[str, bool]:
        """
        Handles validation of user input from a rename dialog.

        Args:
            dialog_result (dict or None): Must include 'name', 'institute', and 'sample_ID'.

        Returns:
            tuple[str, bool]: Sanitized prefix and validity flag, or error message and False.
        """
        if dialog_result is None:
            return "User cancelled the dialog.", False

        user_id = dialog_result.get("name", "").strip()
        institute = dialog_result.get("institute", "").strip()
        sample_id = dialog_result.get("sample_ID", "").strip()

        if not user_id or not institute or not sample_id:
            return "All fields are required.", False

        raw_prefix = f"{user_id}{ID_SEP}{institute}{ID_SEP}{sample_id}"
        sanitized, is_valid = cls.sanitize_and_validate(raw_prefix)

        if not is_valid:
            return "Invalid Parts", False

        return sanitized, True
