# test_id_generator.py

import pytest
from src.records.id_generator import IdGenerator
from src.config.settings import DEVICE_TYPE, ID_SEP

EXPECTED_PREFIX = f"{DEVICE_TYPE.lower()}{ID_SEP}"
TEST_CASES = [
    ("mus-ipat-Sample_A", f"{EXPECTED_PREFIX}mus-ipat-sample_a"),
    ("abc-xyz-sample_1", f"{EXPECTED_PREFIX}abc-xyz-sample_1"),
    ("MUS-IPAT-SAMPLE B", f"{EXPECTED_PREFIX}mus-ipat-sample b"),
]

@pytest.mark.parametrize("filename_prefix, expected_id", TEST_CASES)
def test_generate_record_id(filename_prefix, expected_id):
    record_id = IdGenerator.generate_record_id(filename_prefix)
    assert record_id == expected_id


EXPECTED_FILE_PREFIX = f"{DEVICE_TYPE}{ID_SEP}"
TEST_FILE_ID_CASES = [
    ("mus-ipat-sample_a", f"{EXPECTED_FILE_PREFIX}sample_a"),
    ("ABC-XYZ-sample_1", f"{EXPECTED_FILE_PREFIX}sample_1"),
]

@pytest.mark.parametrize("filename_prefix, expected_file_id", TEST_FILE_ID_CASES)
def test_generate_file_id(filename_prefix, expected_file_id):
    """
    Ensures generate_file_id() extracts the sample ID from the prefix and
    prefixes it with the device type.
    """
    file_id = IdGenerator.generate_file_id(filename_prefix)
    assert file_id == expected_file_id
