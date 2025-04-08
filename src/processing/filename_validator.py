import re
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
        """
        if not FILENAME_PATTERN.match(raw_prefix):
            logger.debug(f"Prefix '{raw_prefix}' failed regex match.")
            return False
        return raw_prefix.count(ID_SEP) >= 2

    @staticmethod
    def sanitize_prefix(raw_prefix: str) -> str:
        """
        Sanitizes a raw filename prefix:
        - Lowercases user ID and institute
        - Replaces spaces with underscores in the sample ID
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
        """
        if not cls.is_valid_prefix(raw_prefix):
            return raw_prefix, False
        return cls.sanitize_prefix(raw_prefix), True

    @staticmethod
    def explain_filename_violation(filename: str) -> dict:
        """
        Returns a dictionary with information on which parts of the filename
        are invalid. Highlights:
        - All hyphens if segment count is incorrect.
        - Individual invalid characters in user/institute/sample segments.
        """
        result = {
            "valid": True,
            "reasons": [],
            "highlight_spans": []  # list of (start_index, end_index) for bad chars
        }

        if not FILENAME_PATTERN.match(filename):
            result["valid"] = False
            segments = filename.split(ID_SEP)

            if len(segments) != 3:
                result["reasons"].append(
                    f"Filename must have exactly 3 parts separated by '{ID_SEP}'."
                )
                for i, char in enumerate(filename):
                    if char == ID_SEP:
                        result["highlight_spans"].append((i, i+1))
            else:
                user, institute, sample = segments

                # --- Track positions of segments in full filename ---
                user_start = 0
                user_end = len(user)

                inst_start = user_end + 1
                inst_end = inst_start + len(institute)

                sample_start = inst_end + 1
                sample_end = len(filename)

                # --- Check user ID ---
                if not re.fullmatch(r"[A-Za-z]+", user):
                    result["reasons"].append("User ID must contain only letters.")
                    for i, char in enumerate(user):
                        if not re.match(r"[A-Za-z]", char):
                            result["highlight_spans"].append((user_start + i, user_start + i + 1))

                # --- Check institute ---
                if not re.fullmatch(r"[A-Za-z]+", institute):
                    result["reasons"].append("Institute must contain only letters.")
                    for i, char in enumerate(institute):
                        if not re.match(r"[A-Za-z]", char):
                            result["highlight_spans"].append((inst_start + i, inst_start + i + 1))

                # --- Check sample ID ---
                if not re.match(r"^[A-Za-z0-9_ ]{1,30}$", sample):
                    result["reasons"].append(
                        "Sample may only contain letters, digits, underscores/spaces, <30 chars."
                    )
                    for i, char in enumerate(sample):
                        if not re.match(r"[A-Za-z0-9_ ]", char):
                            result["highlight_spans"].append((sample_start + i, sample_start + i + 1))

        return result
    
@classmethod
def analyze_user_input(cls, dialog_result: dict | None) -> dict:
    """
    Combines user-input parsing + sanitization + violation explanation.

    Returns:
        {
            "valid": bool,
            "sanitized": str or None,
            "reasons": list[str],
            "highlight_spans": list[tuple[int,int]]
        }
    """
    output = {
        "valid": True,
        "sanitized": None,
        "reasons": [],
        "highlight_spans": []
    }

    if dialog_result is None:
        output["valid"] = False
        output["reasons"].append("User cancelled the dialog.")
        return output

    user_id = dialog_result.get("name", "").strip()
    institute = dialog_result.get("institute", "").strip()
    sample_id = dialog_result.get("sample_ID", "").strip()

    # Build raw prefix and calculate index spans for parts
    raw_prefix = f"{user_id}{ID_SEP}{institute}{ID_SEP}{sample_id}"
    u_start = 0
    u_end = len(user_id)
    i_start = u_end + 1
    i_end = i_start + len(institute)
    s_start = i_end + 1
    s_end = s_start + len(sample_id)

    any_empty = False
    if not user_id:
        output["reasons"].append("User ID is required.")
        output["highlight_spans"].append((u_start, u_end or u_start + 1))
        any_empty = True
    if not institute:
        output["reasons"].append("Institute is required.")
        output["highlight_spans"].append((i_start, i_end or i_start + 1))
        any_empty = True
    if not sample_id:
        output["reasons"].append("Sample ID is required.")
        output["highlight_spans"].append((s_start, s_end or s_start + 1))
        any_empty = True

    if any_empty:
        output["valid"] = False
        return output

    sanitized, is_valid = cls.sanitize_and_validate(raw_prefix)
    if is_valid:
        output["sanitized"] = sanitized
    else:
        output["valid"] = False
        violation_info = cls.explain_filename_violation(raw_prefix)
        output["reasons"].extend(violation_info["reasons"])
        output["highlight_spans"].extend(violation_info["highlight_spans"])

    return output
