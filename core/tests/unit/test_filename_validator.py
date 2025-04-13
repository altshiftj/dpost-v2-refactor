import pytest
from core.processing.filename_validator import FilenameValidator


# --- sanitize_and_validate ---
@pytest.mark.parametrize(
    "raw, expected, valid",
    [
        ("A-B-S", "a-b-S", True),  # minimal valid structure
        (
            "User-Institute-Sample 123",
            "user-institute-Sample_123",
            True,
        ),  # spaces + digits
        (
            "User-Institute-Sample@Name",
            "User-Institute-Sample@Name",
            False,
        ),  # invalid char
        ("123-Org-Sample", "123-Org-Sample", False),  # user ID starts with digits
        (
            "user-org-sample name too long " + "x" * 25,
            "user-org-sample name too long " + "x" * 25,
            False,
        ),  # sample > 30
    ],
)
def test_sanitize_and_validate(raw, expected, valid):
    result, is_valid = FilenameValidator.sanitize_and_validate(raw)
    assert is_valid == valid
    assert result == expected


# --- is_valid_prefix ---
@pytest.mark.parametrize(
    "value, expected",
    [
        ("abc-def-sample1", True),  # valid prefix
        ("abc-def", False),  # not enough parts
        ("abc--sample1", False),  # double dash
        ("abc.def-sample1", False),  # invalid chars
    ],
)
def test_is_valid_prefix(value, expected):
    assert FilenameValidator.is_valid_prefix(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            " user - inst - sample one ",
            "user-inst-sample_one",
        ),  # trims spaces, handle spaces in sample
        (
            "User-Org-Sample With Spaces",
            "user-org-Sample_With_Spaces",
        ),  # spaces handled
        ("User-Org- Sample ", "user-org-Sample"),  # missing sample content prefix
    ],
)
def test_sanitize_prefix_extra_cases(value, expected):
    assert FilenameValidator.sanitize_prefix(value) == expected


# --- analyze_user_input ---
def test_analyze_user_input_valid():
    dialog = {"name": "User", "institute": "Org", "sample_ID": "My Sample"}
    result = FilenameValidator.analyze_user_input(dialog)
    assert result["valid"] is True
    assert result["sanitized"] == "user-org-My_Sample"
    assert result["reasons"] == []
    assert result["highlight_spans"] == []


def test_analyze_user_input_cancelled():
    result = FilenameValidator.analyze_user_input(None)
    assert result["valid"] is False
    assert "User cancelled the dialog." in result["reasons"]


def test_analyze_user_input_invalid_format():
    dialog = {"name": "Bad--Name", "institute": "Oops", "sample_ID": "Sample"}
    result = FilenameValidator.analyze_user_input(dialog)
    assert result["valid"] is False
    assert any(
        "must have exactly 3 parts" in r or "only letters" in r
        for r in result["reasons"]
    )
    assert any(isinstance(span, tuple) for span in result["highlight_spans"])


@pytest.mark.parametrize(
    "dialog, expected_valid, reason_substr",
    [
        (
            {"name": "123", "institute": "Org", "sample_ID": "Sample"},
            False,
            "User ID must contain only letters.",
        ),
        (
            {"name": "User", "institute": "123", "sample_ID": "S"},
            False,
            "Institute must contain only letters",
        ),
        (
            {
                "name": "User",
                "institute": "Org",
                "sample_ID": "This name is definitely over thirty characters long",
            },
            False,
            "30 characters or fewer",
        ),
        (
            {"name": "User", "institute": "Org", "sample_ID": "Sample$Name"},
            False,
            "Sample may only contain letters",
        ),
    ],
)
def test_analyze_user_input_reasons(dialog, expected_valid, reason_substr):
    result = FilenameValidator.analyze_user_input(dialog)
    assert result["valid"] == expected_valid
    assert any(reason_substr in r for r in result["reasons"])
