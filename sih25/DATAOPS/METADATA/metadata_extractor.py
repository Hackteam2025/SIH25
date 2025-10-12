#!/usr/bin/env python3
"""
Metadata Extractor for Argo Float NetCDF Files
Extracts and structures metadata from .nc metadata files for vector DB storage
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import xarray as xr
from datetime import datetime


class ArgoMetadataExtractor:
    """Extract structured metadata from Argo NetCDF metadata files"""

    def __init__(self):
        self.metadata_variables = [
            # Platform identification
            'PLATFORM_NUMBER', 'WMO_INST_TYPE', 'PLATFORM_TYPE',
            'PLATFORM_FAMILY', 'PLATFORM_MAKER',

            # Project and PI info
            'PROJECT_NAME', 'PI_NAME', 'DATA_CENTRE',

            # Deployment info
            'LAUNCH_DATE', 'LAUNCH_LATITUDE', 'LAUNCH_LONGITUDE',
            'DEPLOYMENT_PLATFORM', 'DEPLOYMENT_CRUISE_ID',

            # Technical specs
            'FIRMWARE_VERSION', 'MANUAL_VERSION', 'FLOAT_SERIAL_NO',
            'TRANS_SYSTEM', 'TRANS_FREQUENCY', 'POSITIONING_SYSTEM',

            # Configuration
            'BATTERY_TYPE', 'BATTERY_PACKS',
            'CONTROLLER_BOARD_TYPE_PRIMARY', 'CONTROLLER_BOARD_SERIAL_NO_PRIMARY',

            # Mission info
            'START_DATE', 'END_MISSION_DATE', 'END_MISSION_STATUS',

            # Sensors
            'SENSOR', 'SENSOR_MAKER', 'SENSOR_MODEL', 'SENSOR_SERIAL_NO',

            # Parameters
            'PARAMETER', 'PARAMETER_SENSOR', 'PARAMETER_UNITS',
            'PARAMETER_ACCURACY', 'PARAMETER_RESOLUTION'
        ]

    def _decode_char_array(self, char_array) -> str:
        """Safely decode character arrays from NetCDF"""
        if char_array is None:
            return ""

        try:
            if hasattr(char_array, 'tobytes'):
                decoded = char_array.tobytes().decode('ascii', errors='ignore').strip()
                return decoded.rstrip('\x00')
            elif isinstance(char_array, bytes):
                decoded = char_array.decode('ascii', errors='ignore').strip()
                return decoded.rstrip('\x00')
            elif isinstance(char_array, np.ndarray):
                # Handle character arrays
                if char_array.dtype.kind == 'S':  # Byte string
                    decoded = char_array.tobytes().decode('ascii', errors='ignore').strip()
                    return decoded.rstrip('\x00')
                else:
                    chars = []
                    for c in char_array.flatten():
                        if isinstance(c, bytes):
                            chars.append(c.decode('ascii', errors='ignore'))
                        elif isinstance(c, (int, np.integer)) and c != 0:
                            chars.append(chr(int(c)))
                        elif isinstance(c, str):
                            chars.append(c)
                    result = ''.join(chars).strip()
                    return result.rstrip('\x00')
            else:
                return str(char_array).strip().rstrip('\x00')
        except Exception as e:
            return str(char_array)

    def extract_metadata(self, nc_file_path: str) -> Dict[str, Any]:
        """
        Extract all relevant metadata from an Argo metadata NetCDF file

        Args:
            nc_file_path: Path to the .nc metadata file

        Returns:
            Dictionary with structured metadata
        """
        nc_file = Path(nc_file_path)

        if not nc_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {nc_file}")

        metadata = {
            'source_file': nc_file.name,
            'extraction_timestamp': datetime.now().isoformat(),
            'float_identification': {},
            'deployment_info': {},
            'technical_specs': {},
            'sensors': [],
            'parameters': [],
            'mission_info': {},
            'configuration': {},
            'raw_attributes': {}
        }

        try:
            # Open NetCDF file
            with xr.open_dataset(nc_file, decode_cf=False) as ds:

                # Extract global attributes
                for attr_name in ds.attrs:
                    metadata['raw_attributes'][attr_name] = self._decode_char_array(ds.attrs[attr_name])

                # Float Identification
                if 'PLATFORM_NUMBER' in ds.variables:
                    metadata['float_identification']['platform_number'] = self._decode_char_array(
                        ds['PLATFORM_NUMBER'].values
                    )

                if 'WMO_INST_TYPE' in ds.variables:
                    metadata['float_identification']['wmo_inst_type'] = self._decode_char_array(
                        ds['WMO_INST_TYPE'].values
                    )

                if 'PLATFORM_TYPE' in ds.variables:
                    metadata['float_identification']['platform_type'] = self._decode_char_array(
                        ds['PLATFORM_TYPE'].values
                    )

                if 'PLATFORM_FAMILY' in ds.variables:
                    metadata['float_identification']['platform_family'] = self._decode_char_array(
                        ds['PLATFORM_FAMILY'].values
                    )

                if 'PLATFORM_MAKER' in ds.variables:
                    metadata['float_identification']['platform_maker'] = self._decode_char_array(
                        ds['PLATFORM_MAKER'].values
                    )

                # Deployment Info
                if 'LAUNCH_DATE' in ds.variables:
                    metadata['deployment_info']['launch_date'] = self._decode_char_array(
                        ds['LAUNCH_DATE'].values
                    )

                if 'LAUNCH_LATITUDE' in ds.variables:
                    try:
                        metadata['deployment_info']['launch_latitude'] = float(ds['LAUNCH_LATITUDE'].values)
                    except:
                        metadata['deployment_info']['launch_latitude'] = None

                if 'LAUNCH_LONGITUDE' in ds.variables:
                    try:
                        metadata['deployment_info']['launch_longitude'] = float(ds['LAUNCH_LONGITUDE'].values)
                    except:
                        metadata['deployment_info']['launch_longitude'] = None

                if 'DEPLOYMENT_PLATFORM' in ds.variables:
                    metadata['deployment_info']['deployment_platform'] = self._decode_char_array(
                        ds['DEPLOYMENT_PLATFORM'].values
                    )

                if 'DEPLOYMENT_CRUISE_ID' in ds.variables:
                    metadata['deployment_info']['deployment_cruise_id'] = self._decode_char_array(
                        ds['DEPLOYMENT_CRUISE_ID'].values
                    )

                # Project and PI Info
                if 'PROJECT_NAME' in ds.variables:
                    metadata['deployment_info']['project_name'] = self._decode_char_array(
                        ds['PROJECT_NAME'].values
                    )

                if 'PI_NAME' in ds.variables:
                    metadata['deployment_info']['pi_name'] = self._decode_char_array(
                        ds['PI_NAME'].values
                    )

                if 'DATA_CENTRE' in ds.variables:
                    metadata['deployment_info']['data_centre'] = self._decode_char_array(
                        ds['DATA_CENTRE'].values
                    )

                # Technical Specs
                if 'FIRMWARE_VERSION' in ds.variables:
                    metadata['technical_specs']['firmware_version'] = self._decode_char_array(
                        ds['FIRMWARE_VERSION'].values
                    )

                if 'MANUAL_VERSION' in ds.variables:
                    metadata['technical_specs']['manual_version'] = self._decode_char_array(
                        ds['MANUAL_VERSION'].values
                    )

                if 'FLOAT_SERIAL_NO' in ds.variables:
                    metadata['technical_specs']['float_serial_no'] = self._decode_char_array(
                        ds['FLOAT_SERIAL_NO'].values
                    )

                if 'TRANS_SYSTEM' in ds.variables:
                    metadata['technical_specs']['trans_system'] = self._decode_char_array(
                        ds['TRANS_SYSTEM'].values
                    )

                if 'POSITIONING_SYSTEM' in ds.variables:
                    metadata['technical_specs']['positioning_system'] = self._decode_char_array(
                        ds['POSITIONING_SYSTEM'].values
                    )

                # Configuration
                if 'BATTERY_TYPE' in ds.variables:
                    metadata['configuration']['battery_type'] = self._decode_char_array(
                        ds['BATTERY_TYPE'].values
                    )

                if 'BATTERY_PACKS' in ds.variables:
                    metadata['configuration']['battery_packs'] = self._decode_char_array(
                        ds['BATTERY_PACKS'].values
                    )

                # Mission Info
                if 'START_DATE' in ds.variables:
                    metadata['mission_info']['start_date'] = self._decode_char_array(
                        ds['START_DATE'].values
                    )

                if 'END_MISSION_DATE' in ds.variables:
                    metadata['mission_info']['end_mission_date'] = self._decode_char_array(
                        ds['END_MISSION_DATE'].values
                    )

                if 'END_MISSION_STATUS' in ds.variables:
                    metadata['mission_info']['end_mission_status'] = self._decode_char_array(
                        ds['END_MISSION_STATUS'].values
                    )

                # Sensors
                if 'SENSOR' in ds.variables:
                    sensor_data = ds['SENSOR'].values
                    sensor_maker_data = ds['SENSOR_MAKER'].values if 'SENSOR_MAKER' in ds.variables else None
                    sensor_model_data = ds['SENSOR_MODEL'].values if 'SENSOR_MODEL' in ds.variables else None
                    sensor_serial_data = ds['SENSOR_SERIAL_NO'].values if 'SENSOR_SERIAL_NO' in ds.variables else None

                    # Handle multi-dimensional sensor arrays
                    if sensor_data.ndim >= 2:
                        for i in range(sensor_data.shape[0]):
                            sensor_name = self._decode_char_array(sensor_data[i])
                            if sensor_name:
                                sensor_info = {'sensor_name': sensor_name}

                                if sensor_maker_data is not None:
                                    sensor_info['maker'] = self._decode_char_array(sensor_maker_data[i])
                                if sensor_model_data is not None:
                                    sensor_info['model'] = self._decode_char_array(sensor_model_data[i])
                                if sensor_serial_data is not None:
                                    sensor_info['serial_no'] = self._decode_char_array(sensor_serial_data[i])

                                metadata['sensors'].append(sensor_info)

                # Parameters
                if 'PARAMETER' in ds.variables:
                    param_data = ds['PARAMETER'].values
                    param_sensor_data = ds['PARAMETER_SENSOR'].values if 'PARAMETER_SENSOR' in ds.variables else None
                    param_units_data = ds['PARAMETER_UNITS'].values if 'PARAMETER_UNITS' in ds.variables else None
                    param_accuracy_data = ds['PARAMETER_ACCURACY'].values if 'PARAMETER_ACCURACY' in ds.variables else None
                    param_resolution_data = ds['PARAMETER_RESOLUTION'].values if 'PARAMETER_RESOLUTION' in ds.variables else None

                    # Handle multi-dimensional parameter arrays
                    if param_data.ndim >= 2:
                        for i in range(param_data.shape[0]):
                            param_name = self._decode_char_array(param_data[i])
                            if param_name:
                                param_info = {'parameter_name': param_name}

                                if param_sensor_data is not None:
                                    param_info['sensor'] = self._decode_char_array(param_sensor_data[i])
                                if param_units_data is not None:
                                    param_info['units'] = self._decode_char_array(param_units_data[i])
                                if param_accuracy_data is not None:
                                    param_info['accuracy'] = self._decode_char_array(param_accuracy_data[i])
                                if param_resolution_data is not None:
                                    param_info['resolution'] = self._decode_char_array(param_resolution_data[i])

                                metadata['parameters'].append(param_info)

        except Exception as e:
            metadata['extraction_error'] = str(e)
            print(f"Error extracting metadata from {nc_file}: {e}")

        return metadata

    def create_searchable_text(self, metadata: Dict[str, Any]) -> str:
        """
        Create a searchable text document from metadata for vector embedding

        Args:
            metadata: Structured metadata dictionary

        Returns:
            Formatted text suitable for embedding
        """
        text_parts = []

        # Header
        platform_num = metadata.get('float_identification', {}).get('platform_number', 'Unknown')
        text_parts.append(f"Argo Float Metadata - Platform: {platform_num}")
        text_parts.append("")

        # Float Identification
        float_id = metadata.get('float_identification', {})
        if float_id:
            text_parts.append("## Float Identification")
            for key, value in float_id.items():
                if value:
                    text_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            text_parts.append("")

        # Deployment Information
        deployment = metadata.get('deployment_info', {})
        if deployment:
            text_parts.append("## Deployment Information")
            for key, value in deployment.items():
                if value:
                    text_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            text_parts.append("")

        # Technical Specifications
        tech_specs = metadata.get('technical_specs', {})
        if tech_specs:
            text_parts.append("## Technical Specifications")
            for key, value in tech_specs.items():
                if value:
                    text_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            text_parts.append("")

        # Configuration
        config = metadata.get('configuration', {})
        if config:
            text_parts.append("## Configuration")
            for key, value in config.items():
                if value:
                    text_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            text_parts.append("")

        # Mission Information
        mission = metadata.get('mission_info', {})
        if mission:
            text_parts.append("## Mission Information")
            for key, value in mission.items():
                if value:
                    text_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            text_parts.append("")

        # Sensors
        sensors = metadata.get('sensors', [])
        if sensors:
            text_parts.append("## Sensors")
            for sensor in sensors:
                sensor_desc = f"Sensor: {sensor.get('sensor_name', 'Unknown')}"
                if sensor.get('maker'):
                    sensor_desc += f" (Maker: {sensor['maker']})"
                if sensor.get('model'):
                    sensor_desc += f" Model: {sensor['model']}"
                if sensor.get('serial_no'):
                    sensor_desc += f" S/N: {sensor['serial_no']}"
                text_parts.append(f"- {sensor_desc}")
            text_parts.append("")

        # Parameters
        parameters = metadata.get('parameters', [])
        if parameters:
            text_parts.append("## Measured Parameters")
            for param in parameters:
                param_desc = f"Parameter: {param.get('parameter_name', 'Unknown')}"
                if param.get('sensor'):
                    param_desc += f" (Sensor: {param['sensor']})"
                if param.get('units'):
                    param_desc += f" Units: {param['units']}"
                if param.get('accuracy'):
                    param_desc += f" Accuracy: {param['accuracy']}"
                text_parts.append(f"- {param_desc}")
            text_parts.append("")

        return "\n".join(text_parts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python metadata_extractor.py <metadata_nc_file> [output_json]")
        sys.exit(1)

    nc_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    extractor = ArgoMetadataExtractor()

    # Extract metadata
    print(f"Extracting metadata from: {nc_file}")
    metadata = extractor.extract_metadata(nc_file)

    # Create searchable text
    searchable_text = extractor.create_searchable_text(metadata)

    # Print summary
    print("\n" + "="*80)
    print("EXTRACTED METADATA SUMMARY")
    print("="*80)
    print(searchable_text)
    print("="*80)

    # Save to JSON if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump({
                'metadata': metadata,
                'searchable_text': searchable_text
            }, f, indent=2)
        print(f"\nMetadata saved to: {output_file}")
    else:
        # Print JSON to stdout
        print("\n" + "="*80)
        print("JSON OUTPUT")
        print("="*80)
        print(json.dumps(metadata, indent=2))
