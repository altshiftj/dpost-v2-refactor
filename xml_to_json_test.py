import xml.etree.ElementTree as ET
import tifffile
import json

def parse_fei_image(xml_string):
    # Parse XML data
    root = ET.fromstring(xml_string)
    
    # Image Metadata
    image_metadata = {
        "ImageMetadata": {
            "databarHeight": int(root.find("databarHeight").text),
            "databarFields": int(root.find("databarFields").text),
            "databarLabel": root.find("databarLabel").text,
            "displayWidth": float(root.find("displayWidth").text),
            "pixelWidth": {
                "value": float(root.find("pixelWidth").text),
                "unit": root.find("pixelWidth").attrib["unit"]
            },
            "pixelHeight": {
                "value": float(root.find("pixelHeight").text),
                "unit": root.find("pixelHeight").attrib["unit"]
            },
            "integrations": int(root.find("integrations").text),
            "cropHint": {
                "left": int(root.find("cropHint/left").text),
                "top": int(root.find("cropHint/top").text),
                "right": int(root.find("cropHint/right").text),
                "bottom": int(root.find("cropHint/bottom").text)
            },
            "appliedContrast": float(root.find("appliedContrast").text),
            "appliedBrightness": float(root.find("appliedBrightness").text),
            "appliedGamma": int(root.find("appliedGamma").text),
            "displayBlackLevel": int(root.find("displayBlackLevel").text),
            "displayWhiteLevel": int(root.find("displayWhiteLevel").text),
            "samplePosition": {
                "x": float(root.find("samplePosition/x").text),
                "y": float(root.find("samplePosition/y").text)
            },
            "samplePressureEstimate": float(root.find("samplePressureEstimate").text),
            "workingDistance": {
                "value": float(root.find("workingDistance").text),
                "unit": root.find("workingDistance").attrib["unit"]
            }
        }
    }
    
    # Instrument Metadata
    instrument_metadata = {
        "InstrumentMetadata": {
            "instrument": {
                "type": root.find("instrument/type").text,
                "softwareVersion": root.find("instrument/softwareVersion").text,
                "uniqueID": root.find("instrument/uniqueID").text,
                "edition": root.find("instrument/edition").text,
                "sampleHolder": {
                    "type": int(root.find("instrument/sampleHolder/type").text),
                    "id": root.find("instrument/sampleHolder/id").text
                }
            },
            "applicationID": root.find("applicationID").text,
            "PPI": {
                "version": root.find("PPI/version").text
            },
            "acquisition": {
                "scan": {
                    "scanHW": root.find("acquisition/scan/scanHW").text,
                    "acqHW": root.find("acquisition/scan/acqHW").text,
                    "dwellTime": {
                        "value": int(root.find("acquisition/scan/dwellTime").text),
                        "unit": root.find("acquisition/scan/dwellTime").attrib["unit"]
                    },
                    "spotSize": float(root.find("acquisition/scan/spotSize").text),
                    "spotPresetName": root.find("acquisition/scan/spotPresetName").text,
                    "rotation": int(root.find("acquisition/scan/rotation").text),
                    "interlace": int(root.find("acquisition/scan/interlace").text),
                    "detector": root.find("acquisition/scan/detector").text,
                    "detectorMixFactors": {
                        "bsdA": float(root.find("acquisition/scan/detectorMixFactors/bsdA").text),
                        "bsdB": float(root.find("acquisition/scan/detectorMixFactors/bsdB").text),
                        "bsdC": float(root.find("acquisition/scan/detectorMixFactors/bsdC").text),
                        "bsdD": float(root.find("acquisition/scan/detectorMixFactors/bsdD").text),
                        "sed": float(root.find("acquisition/scan/detectorMixFactors/sed").text)
                    },
                    "detectors": {
                        "QBSD": {
                            "gain": float(root.find("acquisition/scan/detectors/QBSD/gain").text),
                            "offset": float(root.find("acquisition/scan/detectors/QBSD/offset").text),
                            "mixFactor": float(root.find("acquisition/scan/detectors/QBSD/mixFactor").text)
                        },
                        "SED": {
                            "gain": float(root.find("acquisition/scan/detectors/SED/gain").text),
                            "offset": float(root.find("acquisition/scan/detectors/SED/offset").text),
                            "scintillatorVoltage": float(root.find("acquisition/scan/detectors/SED/scintillatorVoltage").text),
                            "mixFactor": float(root.find("acquisition/scan/detectors/SED/mixFactor").text)
                        }
                    },
                    "beamShift": {
                        "x": float(root.find("acquisition/scan/beamShift/x").text),
                        "y": float(root.find("acquisition/scan/beamShift/y").text)
                    },
                    "sourceTilt": {
                        "x": float(root.find("acquisition/scan/sourceTilt/x").text),
                        "y": float(root.find("acquisition/scan/sourceTilt/y").text)
                    },
                    "stigmator": {
                        "x": float(root.find("acquisition/scan/stigmator/x").text),
                        "y": float(root.find("acquisition/scan/stigmator/y").text)
                    },
                    "sourceTime": {
                        "value": int(root.find("acquisition/scan/sourceTime").text),
                        "unit": root.find("acquisition/scan/sourceTime").attrib["unit"]
                    },
                    "sourceId": int(root.find("acquisition/scan/sourceId").text),
                    "highVoltage": {
                        "value": float(root.find("acquisition/scan/highVoltage").text),
                        "unit": root.find("acquisition/scan/highVoltage").attrib["unit"]
                    },
                    "emissionCurrent": {
                        "value": float(root.find("acquisition/scan/emissionCurrent").text),
                        "unit": root.find("acquisition/scan/emissionCurrent").attrib["unit"]
                    },
                    "emissionCurrentPresetName": root.find("acquisition/scan/emissionCurrentPresetName").text,
                    "filamentPower": {
                        "value": float(root.find("acquisition/scan/filamentPower").text),
                        "unit": root.find("acquisition/scan/filamentPower").attrib["unit"]
                    },
                    "scanCenter": {
                        "x": float(root.find("acquisition/scan/scanCenter/x").text),
                        "y": float(root.find("acquisition/scan/scanCenter/y").text)
                    },
                    "scanScale": int(root.find("acquisition/scan/scanScale").text)
                }
            },
            "multiStage": {
                "axis": {
                    "X": float(root.find("multiStage/axis[@id='X']").text),
                    "Y": float(root.find("multiStage/axis[@id='Y']").text)
                },
                "sampleRadius": {
                    "value": int(root.find("multiStage/sampleRadius").text),
                    "unit": root.find("multiStage/sampleRadius").attrib["unit"]
                },
                "sampleHeight": {
                    "value": int(root.find("multiStage/sampleHeight").text),
                    "unit": root.find("multiStage/sampleHeight").attrib["unit"]
                }
            }
        }
    }
    
    # Advanced Metadata
    advanced_metadata = {
        "AdvancedMetadata": {
            "NewSubfileType": int(root.find("NewSubfileType").text),
            "Compression": int(root.find("Compression").text),
            "Predictor": int(root.find("Predictor").text),
            "BitsPerSample": int(root.find("BitsPerSample").text),
            "SamplesPerPixel": int(root.find("SamplesPerPixel").text),
            "RowsPerStrip": int(root.find("RowsPerStrip").text),
            "StripOffsets": [int(value) for value in root.find("StripOffsets").text.strip("()").split(", ")],
            "StripByteCounts": [int(value) for value in root.find("StripByteCounts").text.strip("()").split(", ")],
            "PhotometricInterpretation": int(root.find("PhotometricInterpretation").text),
            "ResolutionUnit": int(root.find("ResolutionUnit").text),
            "XResolution": [int(value) for value in root.find("XResolution").text.strip("()").split(", ")],
            "YResolution": [int(value) for value in root.find("YResolution").text.strip("()").split(", ")]
        }
    }
    
    # Combine all dictionaries into one final dictionary
    final_data = {**image_metadata, **instrument_metadata, **advanced_metadata}
    
    return json.dumps(final_data, indent=4)

# Extract XML from TIFF file
tiff_file_path = "SEM_Test.tiff"  # Replace with your TIFF file path

try:
    # Read the TIFF file
    with tifffile.TiffFile(tiff_file_path) as tif:
            # Extract tags from the first page
            page = tif.pages[0]
            tags = page.tags

            # Process TIFF tags
            for tag in tags.values():
                tag_name = tag.name
                tag_value = tag.value
                # Convert bytes to string if necessary
                if isinstance(tag_value, bytes):
                    try:
                        tag_value = tag_value.decode('utf-8')
                    except UnicodeDecodeError:
                        tag_value = tag_value.decode('latin-1')
        else:
            raise ValueError("No XML metadata found in the TIFF file.")
    
    # Ensure XML data is correctly extracted
    if not xml_data:
        raise ValueError("The XML data in the TIFF file is empty or improperly formatted.")

    # Parse the XML data and convert it to JSON
    parsed_json = parse_fei_image(xml_data)
    print(parsed_json)

except ET.ParseError as e:
    print(f"XML Parsing Error: {e}")
except Exception as e:
    print(f"Error: {e}")
