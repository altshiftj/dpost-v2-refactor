"""
Currently not implemented in the application. Someday...
"""

import os
import re
import hashlib
import xmltodict
import tifffile
from ipat_watchdog.app.logger import setup_logger

logger = setup_logger(__name__)


class MetadataExtractor:
    @staticmethod
    def hash_file(file_path, chunk_size=65536):
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as file:
                while True:
                    data = file.read(chunk_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logger.exception(f"Failed to hash file {file_path}: {e}")
            return None

    @staticmethod
    def flatten_xml_dict(d, parent_key="", sep="_"):
        items = {}
        if parent_key.startswith("FeiImage"):
            parent_key = parent_key.replace("FeiImage", "")

        for k, v in d.items():
            if k.startswith("@"):
                attr_name = k[1:]
                new_key = f"{parent_key}{sep}{attr_name}" if parent_key else attr_name
                items[new_key] = v
            elif k == "#text":
                if v.strip():
                    new_key = parent_key if parent_key else "text"
                    items[new_key] = v.strip()
            else:
                new_parent_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.update(
                        MetadataExtractor.flatten_xml_dict(v, new_parent_key, sep=sep)
                    )
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        items.update(
                            MetadataExtractor.flatten_xml_dict(
                                item, f"{new_parent_key}{sep}{i}", sep=sep
                            )
                        )
                elif isinstance(v, tuple):
                    for i, item in enumerate(v):
                        items.update(
                            MetadataExtractor.flatten_xml_dict(
                                item, f"{new_parent_key}{sep}{i}", sep=sep
                            )
                        )
                else:
                    new_key = new_parent_key
                    items[new_key] = v
        return items

    @staticmethod
    def parse_xml_metadata(xml_string):
        try:
            xml_dict = xmltodict.parse(xml_string)
            flat_dict = MetadataExtractor.flatten_xml_dict(xml_dict)
            return flat_dict
        except Exception as e:
            logger.exception(f"Failed to parse XML metadata: {e}")
            return {}

    @staticmethod
    def extract_tiff_metadata(file_path):
        base_name = os.path.basename(file_path)
        file_name, ext = os.path.splitext(base_name)
        file_hash = MetadataExtractor.hash_file(file_path)

        metadata = {}
        flattened_data = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                page = tif.pages[0]
                tags = page.tags

                for tag in tags.values():
                    tag_name = tag.name
                    tag_value = tag.value

                    if isinstance(tag_value, tuple):
                        flattened_data = {
                            f"{tag_name}_{i}": value
                            for i, value in enumerate(tag_value)
                        }

                    if isinstance(tag_value, bytes):
                        try:
                            tag_value = tag_value.decode("utf-8")
                        except UnicodeDecodeError:
                            tag_value = tag_value.decode("latin-1")

                    if flattened_data:
                        metadata.update(flattened_data)
                        flattened_data = {}
                    else:
                        metadata[tag_name] = tag_value

                    if tag_name == "FEI_TITAN":
                        xml_metadata = MetadataExtractor.parse_xml_metadata(tag_value)
                        for k, v in xml_metadata.items():
                            if v is None:
                                xml_metadata[k] = "null"
                            elif re.match(r"^-?\d+$", v):
                                xml_metadata[k] = int(v)
                            elif re.match(r"^-?\d+(\.\d+)?$", v):
                                xml_metadata[k] = float(v)
                            elif re.match(r"^-?\d+(\.\d+)?[eE][-+]?\d+$", v):
                                xml_metadata[k] = float(v)
                        metadata.update(xml_metadata)

            metadata.pop("FEI_TITAN", None)
            metadata.pop("xmlns:xsi", None)
            metadata.pop("xsi:noNamespaceSchemaLocation", None)

            metadata[f"filehash"] = file_hash
            metadata = {f"{file_name}|{k}": v for k, v in metadata.items()}

        except Exception as e:
            logger.exception(f"Failed to extract metadata from {file_path}: {e}")
            return None
        return metadata
