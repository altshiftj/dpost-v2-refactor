import pytest
from src.processing.filename_validator import FilenameValidator

# --- sanitize_and_validate ---
@pytest.mark.parametrize("raw, expected, valid", [
    ("MUS-IPAT-Sample 1",   "mus-ipat-Sample_1",    True),
    ("abc-xyz-sample_01",   "abc-xyz-sample_01",    True),
    ("user--bad",           "user--bad",            False),
    ("no-separators",       "no-separators",        False),
])
def test_sanitize_and_validate(raw, expected, valid):
    result, is_valid = FilenameValidator.sanitize_and_validate(raw)
    assert is_valid == valid
    assert result == expected

# --- is_valid_prefix ---
@pytest.mark.parametrize("value, expected", [
    ("abc-def-sample1",     True),
    ("abc-def",             False),  # not enough parts
    ("abc--sample1",        False),  # double dash
    ("abc.def-sample1",     False),  # invalid chars
])
def test_is_valid_prefix(value, expected):
    assert FilenameValidator.is_valid_prefix(value) == expected

# --- sanitize_prefix ---
@pytest.mark.parametrize("value, expected", [
    ("ABC-IPAT-Sample A",   "abc-ipat-Sample_A"),
    ("user-Institute-s1",   "user-institute-s1"),
    ("badformat",           "badformat"),  # fallback to original
])
def test_sanitize_prefix(value, expected):
    assert FilenameValidator.sanitize_prefix(value) == expected

# --- from_user_input ---
def test_from_user_input_valid():
    dialog = {"name": "User", "institute": "Org", "sample_ID": "My Sample"}
    result, is_valid = FilenameValidator.from_user_input(dialog)
    assert is_valid is True
    assert result == "user-org-My_Sample"

def test_from_user_input_incomplete_fields():
    dialog = {"name": "User", "institute": "", "sample_ID": "My Sample"}
    result, is_valid = FilenameValidator.from_user_input(dialog)
    assert not is_valid
    assert result == "All fields are required."

def test_from_user_input_cancelled():
    result, is_valid = FilenameValidator.from_user_input(None)
    assert not is_valid
    assert result == "User cancelled the dialog."

def test_from_user_input_invalid_format():
    dialog = {"name": "Bad--Name", "institute": "Oops", "sample_ID": "Sample"}
    result, is_valid = FilenameValidator.from_user_input(dialog)
    assert not is_valid
    assert result == "Invalid Parts"
