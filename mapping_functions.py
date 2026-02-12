import hashlib
import json
from datetime import datetime, timezone
import os
import re
from typing import Any, Dict, List, Tuple


# Utility functions
def validate_mapping(mapping_dict: dict) -> str:
    """Validate mapping structure."""
    if not isinstance(mapping_dict, dict):
        return "Invalid mapping: input should be a dictionary"
    if "filter" not in mapping_dict or "mapping" not in mapping_dict:
        return "Invalid mapping: 'filter' and 'mapping' keys are required"
    if not isinstance(mapping_dict["filter"], list) or not isinstance(mapping_dict["mapping"], list):
        return "Invalid mapping: 'filter' should be a list and 'mapping' should be a list"
    if len(mapping_dict["filter"]) == 0 or len(mapping_dict["mapping"]) == 0:
        return "Invalid mapping: 'filter' and 'mapping' cannot be empty"
    for mapping in mapping_dict["mapping"]:
        if not isinstance(mapping, dict):
            return "Invalid mapping: each mapping should be a dictionary"
        if "table_name" not in mapping or "columns" not in mapping:
            return "Invalid mapping: 'mapping' should contain 'table_name' and 'columns'"
        if not isinstance(mapping["table_name"], str) or not isinstance(mapping["columns"], list):
            return "Invalid mapping: 'table_name' should be a string and 'columns' should be a list"
        for col in mapping["columns"]:
            if not all(k in col for k in ("name", "datatype", "mapping")):
                return "Invalid mapping: Each column should have 'name', 'datatype', and 'mapping'"
    return "OK"


def get_value_from_payload(mapping: str, payload: Dict[str, Any]) -> Any:
    """
    Extract value from JSON based on mapping logic.
    Supports:
    - Dot notation for nested keys
    - Array filtering like [type='PreAuth'] or [0]
    - Functions: concat(), rm_extra_spaces(), split(), substring(), int(), decimal(), date(), timestamp(), lower(), upper()
    """
    if payload is None or mapping is None:
        return None

    # Handle quoted literals
    if (mapping.startswith("'") and mapping.endswith("'")) or (mapping.startswith('"') and mapping.endswith('"')):
        return mapping[1:-1]

    # Handle numeric literals, including optional leading + or -
    if isinstance(mapping, str) and re.fullmatch(r'[+-]?\d+(\.\d+)?', mapping.strip()):
        return float(mapping) if '.' in mapping else int(mapping)

    # Find positions of special characters
    dot_pos = mapping.find('.')
    sq_bracket_pos = mapping.find('[')
    round_bracket_pos = mapping.find('(')

    if dot_pos == -1: dot_pos = len(mapping) + 1
    if sq_bracket_pos == -1: sq_bracket_pos = len(mapping) + 1
    if round_bracket_pos == -1: round_bracket_pos = len(mapping) + 1

    # Dot notation
    if dot_pos < sq_bracket_pos and dot_pos < round_bracket_pos:
        if isinstance(payload, dict):
            return get_value_from_payload(mapping[dot_pos + 1:], payload.get(mapping[:dot_pos], None))
        elif isinstance(payload, list):
            return [get_value_from_payload(mapping[dot_pos + 1:], item.get(mapping[:dot_pos], None)) for item in payload if isinstance(item, dict)]
        else:
            return None
    
    # Function handling
    if round_bracket_pos < dot_pos and round_bracket_pos < sq_bracket_pos:
        func_name = mapping[:round_bracket_pos].strip()
        func_end_pos = mapping.rfind(')', round_bracket_pos)
        func_args = mapping[round_bracket_pos + 1:func_end_pos]

        # Split arguments safely
        args = []
        stack, start = [], 0
        for i, ch in enumerate(func_args):
            if ch == '(':
                stack.append('(')
            elif ch == ')':
                if stack: stack.pop()
            elif ch == ',' and not stack:
                args.append(func_args[start:i].strip())
                start = i + 1
        args.append(func_args[start:].strip())

        # Process functions
		# Input: concat('Hello', ' ', 'World ')
        # Output: 'Hello World '
        if func_name == 'concat':
            return ''.join(str(get_value_from_payload(arg, payload) or '') for arg in args)

		# Input: rm_extra_spaces('  Hello   World  ')
        # Output: 'Hello World'
        if func_name == 'rm_extra_spaces':
            val = get_value_from_payload(args[0], payload)
            return ' '.join(val.split()) if isinstance(val, str) else None

		# Input: split('Hello/World', '/'), split('Hello/World', '/')[1]
        # Output: ['Hello', 'World'], 'World'
        if func_name == 'split':
            val = get_value_from_payload(args[0], payload)
            delimiter = get_value_from_payload(args[1], payload)
            if isinstance(val, str) and isinstance(delimiter, str):
                parts = val.split(delimiter)
                rest = mapping[func_end_pos + 1:].strip()
                if rest.startswith('[') and rest.endswith(']'):
                    idx = int(rest[1:-1])
                    return parts[idx] if 0 <= idx < len(parts) else None
                return parts
        
        # Input: len('Hello World')
        # Output: 11
        if func_name == 'len':
            val = get_value_from_payload(args[0], payload)
            return len(val) if isinstance(val, (str, list, dict)) else None
        
        # Input sum(123, 456), sum(123.45, 456.78), sum(123, -456)
        # Output: 579, 580.23, -333
        if func_name == 'sum':
            val1 = get_value_from_payload(args[0], payload)
            val2 = get_value_from_payload(args[1], payload)

            def is_int_like(v):
                if isinstance(v, int):
                    return True
                if isinstance(v, str):
                    return re.fullmatch(r'[+-]?\d+', v.strip()) is not None
                return False
            try:
                if is_int_like(val1) and is_int_like(val2):
                    return int(val1) + int(val2)
                # Fall back to float sum
                return float(val1) + float(val2)
            except (TypeError, ValueError):
                return None

		# Input: substring('HelloWorld', 0, 5), substring('HelloWorld', 5), substring('HelloWorld', ,3)
        # Output: 'Hello', 'World', 'Hel'
        if func_name == 'substring':
            val = get_value_from_payload(args[0], payload)
            if isinstance(val, str):
                start = int(get_value_from_payload(args[1], payload) or 0)
                length = int(get_value_from_payload(args[2], payload) or len(val))
                if start + length > len(val):
                    return val[start:]
                else:
                    return val[start:start + length]
        
        # Input: int('123')
        # Output: 123
        if func_name == 'int':
            val = get_value_from_payload(args[0], payload)
            try:
                return int(val)
            except (TypeError, ValueError):
                return None
        
        # Input: decimal('123.45')
        # Output: 123.45
        if func_name == 'decimal':
            val = get_value_from_payload(args[0], payload)
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

		# Input: date('2024-06-15T12:34:56'), date('2024-06-15')
        # Output: '2024-06-15', '2024-06-15'
        if func_name == 'date':
            val = get_value_from_payload(args[0], payload)
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val.replace('Z', '')).astimezone(timezone.utc).strftime('%Y-%m-%d')
                except ValueError:
                    return None

		# Input: timestamp('2024-06-15T12:34:56Z'), timestamp('2024-06-15 12:34:56')
        # Output: '2024-06-15 12:34:56', '2024-06-15 12:34:56'
        if func_name == 'timestamp':
            val = get_value_from_payload(args[0], payload)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace('Z', ''))
                    return dt.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None

		# Input: lower('Hello World')
        # Output: 'hello world'
        if func_name == 'lower':
            val = get_value_from_payload(args[0], payload)
            return val.lower() if isinstance(val, str) else None
        
        # Input: upper('Hello World')
        # Output: 'HELLO WORLD'
        if func_name == 'upper':
            val = get_value_from_payload(args[0], payload)
            return val.upper() if isinstance(val, str) else None
        
        # Input: nvl(arg1, arg2, ...)
        # Output: first non-null argument
        if func_name == 'nvl':
            for arg in args:
                val = get_value_from_payload(arg, payload)
                if val is not None:
                    return val
            return None


    # Array filter or index
    if sq_bracket_pos < dot_pos and sq_bracket_pos < round_bracket_pos:
        base = mapping[:sq_bracket_pos]
        filter = mapping[sq_bracket_pos + 1:mapping.find(']', sq_bracket_pos)]
        rest = mapping[mapping.find(']', sq_bracket_pos) + 1:]
        if isinstance(payload, dict):
            arr = get_value_from_payload(base, payload)
            if isinstance(arr, list):
                if filter == '': # when no filter provided return all items
                    return_arr = []
                    for arr_element in arr:
                        if rest == '' or rest is None:
                            return_arr.extend(arr_element)
                        else:
                            inside_mapping = get_value_from_payload(rest.lstrip('.'), arr_element)
                            if inside_mapping is not None:
                                return_arr.extend(inside_mapping)
                    return return_arr
                elif '=' in filter:  # filter by = (returns all matches as array or single match as value)
                    key, expected = filter.split('=', 1)
                    expected = expected.strip("'\"")
                    matches = []
                    for item in arr:
                        payload_value = get_value_from_payload(key.strip(), item)
                        if isinstance(item, dict) and isinstance(payload_value, str) and payload_value == expected:
                            if rest == '' or rest is None:
                                matches.append(item)
                            else:
                                match_value = get_value_from_payload(rest.lstrip('.'), item)
                                if match_value is not None:
                                    matches.append(match_value)
                    if len(matches) == 0:
                        return None
                    elif len(matches) == 1:
                        return matches[0]
                    else:
                        return json.dumps(matches)
                elif filter.isdigit():  # filter by index
                    idx = int(filter)
                    if rest == '' or rest is None:
                        return arr[idx] if 0 <= idx < len(arr) else None
                    else:
                        return get_value_from_payload(rest.lstrip('.'), arr[idx]) if 0 <= idx < len(arr) else None

    if isinstance(payload, dict):
        return payload.get(mapping, None)
    elif isinstance(payload, list):
        if len(payload) > 1:
            return [item.get(mapping, None) for item in payload if isinstance(item, dict)]
        else:
            return payload[0].get(mapping, None) if isinstance(payload[0], dict) else None
    elif isinstance(payload, str):
        return payload
    else:
        return None

def validate_datatype(source_value, mapping_datatype):
    """
    Validate and convert source_value to the specified datatype.
    
    Supports: VARCHAR, CHAR, TEXT, INT, SMALLINT, BIGINT, FLOAT, DOUBLE, REAL, 
              DECIMAL, NUMERIC, DATE, TIME, TIMESTAMP, BOOLEAN
    
    Returns:
        Tuple of (validated_value, error_map) where error_map is None if valid, or a dict with error details if invalid.
    """
    if source_value is None:
        return None, None
    
    datatype_upper = mapping_datatype.upper()
    
    try:
        # VARCHAR - variable-length string
        if datatype_upper.startswith('VARCHAR'):
            return str(source_value), None
        
        # CHAR - fixed-length string
        if datatype_upper.startswith('CHAR'):
            char_val = str(source_value)
            # Extract length if specified (e.g., CHAR(4))
            if '(' in datatype_upper:
                length = int(datatype_upper.split('(')[1].split(')')[0])
                if len(char_val) > length:
                    return char_val[:length], {'datatype': mapping_datatype, 'value': source_value, 'error': f'CHAR length exceeds {length}'}
            return char_val, None
        
        # TEXT - large text
        if datatype_upper == 'TEXT':
            return str(source_value), None
        
        # INT - 32-bit integer
        if datatype_upper == 'INT':
            int_val = int(source_value)
            if int_val < -2147483648 or int_val > 2147483647:
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'INT value out of range'}
            return int_val, None
        
        # SMALLINT - 16-bit integer
        if datatype_upper == 'SMALLINT':
            int_val = int(source_value)
            if int_val < -32768 or int_val > 32767:
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'SMALLINT value out of range'}
            return int_val, None
        
        # BIGINT - 64-bit integer
        if datatype_upper == 'BIGINT':
            int_val = int(source_value)
            if int_val < -9223372036854775808 or int_val > 9223372036854775807:
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'BIGINT value out of range'}
            return int_val, None
        
        # FLOAT - single-precision floating-point
        if datatype_upper == 'FLOAT':
            return float(source_value), None
        
        # DOUBLE - double-precision floating-point
        if datatype_upper == 'DOUBLE':
            return float(source_value), None
        
        # REAL - real/single-precision number
        if datatype_upper == 'REAL':
            return float(source_value), None
        
        # DECIMAL - fixed-point decimal (e.g., DECIMAL(18,2))
        if datatype_upper.startswith('DECIMAL'):
            decimal_val = float(source_value)
            # Round to specified scale if provided
            if '(' in datatype_upper:
                precision_scale = datatype_upper.split('(')[1].split(')')[0]
                if ',' in precision_scale:
                    precision, scale = map(int, precision_scale.split(','))
                    # Round to the specified scale
                    decimal_val = round(decimal_val, scale)
            return decimal_val, None
        
        # NUMERIC - fixed-point numeric (e.g., NUMERIC(15,2))
        if datatype_upper.startswith('NUMERIC'):
            numeric_val = float(source_value)
            # Round to specified scale if provided
            if '(' in datatype_upper:
                precision_scale = datatype_upper.split('(')[1].split(')')[0]
                if ',' in precision_scale:
                    precision, scale = map(int, precision_scale.split(','))
                    # Round to the specified scale
                    numeric_val = round(numeric_val, scale)
            return numeric_val, None
        
        # DATE - date only (YYYY-MM-DD)
        if datatype_upper == 'DATE':
            val_str = str(source_value)
            try:
                # Split by 'T' or space to extract date part
                date_part = val_str.split('T')[0] if 'T' in val_str else val_str.split()[0]
                parsed_date = datetime.fromisoformat(date_part).date()
                return parsed_date.isoformat(), None
            except (ValueError, AttributeError, IndexError):
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'Invalid DATE format (expected YYYY-MM-DD)'}
        
        # TIME - time only (HH:MM:SS)
        if datatype_upper == 'TIME':
            val_str = str(source_value)
            try:
                # Split by 'T' or space to extract time part (remove date if present)
                time_part = val_str.split('T')[-1] if 'T' in val_str else val_str.split()[-1]
                
                # Parse time in HH:MM:SS format
                parts = time_part.split(':')
                if len(parts) != 3:
                    raise ValueError("Invalid TIME format")
                hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
                if hour < 0 or hour > 23 or minute < 0 or minute > 59 or second < 0 or second > 59:
                    raise ValueError("TIME values out of range")
                return f"{hour:02d}:{minute:02d}:{second:02d}", None
            except (ValueError, AttributeError, IndexError):
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'Invalid TIME format (expected HH:MM:SS)'}
        
        # TIMESTAMP - date and time with timezone
        if datatype_upper == 'TIMESTAMP':
            val_str = str(source_value)
            try:
                parsed_dt = datetime.fromisoformat(val_str.replace('Z', '+00:00'))
                return parsed_dt.isoformat(), None
            except ValueError:
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'Invalid TIMESTAMP format (expected ISO 8601)'}
        
        # BOOLEAN - true/false values
        if datatype_upper == 'BOOLEAN':
            if isinstance(source_value, bool):
                return source_value, None
            val_str = str(source_value).lower().strip()
            if val_str in ('true', '1', 'yes', 'y', 'on'):
                return True, None
            elif val_str in ('false', '0', 'no', 'n', 'off'):
                return False, None
            else:
                return None, {'datatype': mapping_datatype, 'value': source_value, 'error': 'Invalid BOOLEAN value'}
        
        # If datatype is not recognized, return error
        return None, {'datatype': mapping_datatype, 'value': source_value, 'error': f'Unknown datatype: {mapping_datatype}'}
    
    except (ValueError, TypeError) as e:
        return None, {'datatype': mapping_datatype, 'value': source_value, 'error': f'Validation failed, {str(e)}'}
            

def process_mappings_local(payload_dict: dict, local_path: str) -> dict:
    """
    Go through each mapping JSON file from local path and create dictionary of mapped tables from payload_dict.
    Returned dictionary will have 'error' key storing all files that had issues.
    
    Args:
        payload_dict: The payload to map
        local_path: Local directory path to read mapping files from
    """
    mapped_tables = {}
    
    try:
        # Read from local directory
        if not os.path.exists(local_path):
            return {'error': {'mapping_file': 'N/A', 'error': f'Local path {local_path} does not exist'}}
        
        if not os.path.isdir(local_path):
            return {'error': {'mapping_file': 'N/A', 'error': f'Local path {local_path} is not a directory'}}
        
        all_files = [f for f in os.listdir(local_path) if os.path.isfile(os.path.join(local_path, f))]
        json_files_found = []
        
        # Process each JSON file
        for file_name in all_files:
            if file_name.endswith('.json'):
                json_files_found.append(file_name)
                try:
                    # Read the file from local path
                    file_path = os.path.join(local_path, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    mapping_dict = json.loads(file_content)
                    file_key = file_name  # Use filename for error reporting
                    
                    # Process mapping
                    result = _process_single_mapping(mapping_dict, payload_dict, file_key, mapped_tables)
                    if result:
                        mapped_tables = result
                        
                except Exception as file_err:
                    import traceback
                    mapped_tables.setdefault('error', []).append({'mapping_file': file_name, 'error': str(file_err), 'traceback': traceback.format_exc()})
        
        # Check if any JSON files were found
        if len(json_files_found) == 0:
            return {'error': {'mapping_file': 'N/A', 'error': f'No .json files found in {local_path}. Found {len(all_files)} total files.'}}
            
    except Exception as e:
        import traceback
        mapped_tables.setdefault('error', []).append({'error': str(e), 'traceback': traceback.format_exc()})
    
    return mapped_tables


def _process_single_mapping(mapping_dict: dict, payload_dict: dict, file_key: str, mapped_tables: dict) -> dict:
    """
    Process a single mapping file and update the mapped_tables dictionary.
    
    Args:
        mapping_dict: The loaded mapping configuration
        payload_dict: The payload to map
        file_key: The file identifier (S3 key or local filename)
        mapped_tables: The current mapped tables dictionary
        
    Returns:
        Updated mapped_tables dictionary, or None if error occurred
    """
    validation_result = validate_mapping(mapping_dict)

    if validation_result == 'OK':
        # Check if current mapping_file has any mapping from payload_dict
        # Skip mapping if filter attribute doesn't exist (returns None) or filter doesn't match
        if not any(
            bool(re.match(pattern.get("value", ""), payload_value))
            for pattern in mapping_dict.get('filter', [])
            if (payload_value := get_value_from_payload(pattern.get("attribute", ""), payload_dict)) is not None
        ):
            return mapped_tables  # Skip this mapping_file if no filter matches or attribute missing

        # Map for each table in mapping_dict
        for mapping in mapping_dict['mapping']:
            table_name = mapping['table_name']
            columns = mapping['columns']
            mapped_rows = []

            # Handle flattened mappings
            if "flatten" in mapping:
                flatten_path = mapping["flatten"]
                base_array = get_value_from_payload(flatten_path, payload_dict)
                hash_array = []
                        
                if isinstance(base_array, list):
                    for element in base_array:
                        if isinstance(element, dict):
                            hash_object = hashlib.sha256(json.dumps(element, sort_keys=True).encode('utf-8'))
                            element_hash = hash_object.hexdigest()
                            hash_array.append(element_hash)

                    mapped_rows = [dict() for _ in base_array]
                    for col in columns:
                        if "flattened" in col:
                            # Full flattening
                            if col["flattened"] == "full":
                                for i, item in enumerate(base_array):
                                    validated_value, error_map = validate_datatype(
                                        get_value_from_payload(col["mapping"], item),
                                        col["datatype"]
                                    )
                                    mapped_rows[i][col["name"]] = validated_value
                                    if error_map is not None:
                                        mapped_tables.setdefault('error', []).append(error_map)

                            # Partial flattening which is a subset of flattened path
                            else:
                                partial_flatten_path = col["flattened"]
                                if flatten_path.startswith(partial_flatten_path):
                                    relative_path = flatten_path[len(partial_flatten_path):].lstrip('.[]')
                                    outer_arr = get_value_from_payload(partial_flatten_path, payload_dict)

                                    hash_to_outer_element_map = {}
                                    for outer_element in outer_arr:
                                        base_array_in_outer_element = get_value_from_payload(relative_path, outer_element)
                                        if base_array_in_outer_element is not None and isinstance(base_array_in_outer_element, list) and len(base_array_in_outer_element) > 0:
                                            for element in base_array_in_outer_element:
                                                hash_object = hashlib.sha256(json.dumps(element, sort_keys=True).encode('utf-8'))
                                                current_hash = hash_object.hexdigest()
                                                hash_to_outer_element_map[current_hash] = outer_element
                                    
                                    for i in range(len(base_array)):
                                        current_hash = hash_array[i]
                                        outer_element = hash_to_outer_element_map.get(current_hash, None)
                                        if outer_element is not None and isinstance(outer_element, dict):
                                            validated_value, error_map = validate_datatype(
                                                get_value_from_payload(col["mapping"], outer_element),
                                                col["datatype"]
                                            )
                                            mapped_rows[i][col["name"]] = validated_value
                                            if error_map is not None:
                                                mapped_tables.setdefault('error', []).append(error_map)
                                        else:
                                            mapped_rows[i][col["name"]] = None
                                else:
                                    mapped_rows[i][col["name"]] = None
                        else:
                            for i in range(len(base_array)):
                                validated_value, error_map = validate_datatype(
                                    get_value_from_payload(col["mapping"], payload_dict),
                                    col["datatype"]
                                )
                                mapped_rows[i][col["name"]] = validated_value
                                if error_map is not None:
                                    mapped_tables.setdefault('error', []).append(error_map)

                if len(mapped_rows) > 0:
                    mapped_tables[table_name] = mapped_rows
            else:
                mapped_row = {}
                for col in columns:
                    validated_value, error_map = validate_datatype(
                        get_value_from_payload(col["mapping"], payload_dict),
                        col["datatype"]
                    )
                    mapped_row[col["name"]] = validated_value
                    if error_map is not None:
                        mapped_tables.setdefault('error', []).append(error_map)
                mapped_tables[table_name] = [mapped_row]
        
    else:
        mapped_tables.setdefault('error', []).append({'mapping_file': file_key, 'error': validation_result})
    
    return mapped_tables


def generate_insert_sql(
    table_dict: Dict[str, Any], 
    catalog: str = None, 
    schema: str = None, 
    ignore_empty_columns: bool = True
) -> List[str]:
    """
    Generate batched INSERT SQL statements.

    :param table_dict: Dictionary where keys are table names and values are lists of row dictionaries.
    :param catalog: Optional catalog name to prefix table names.
    :param schema: Optional schema name to prefix table names.
    :param ignore_empty_columns: If True, columns with None values are omitted from the INSERT.
                                 If False, None values are explicitly inserted as NULL.
    """
    insert_statements = []
    table_prefix = f'"{catalog}"."{schema}".' if catalog and schema else (f'"{schema}".' if schema else "")

    for table_name, rows in table_dict.items():
        if table_name == 'error' or not isinstance(rows, list):
            continue

        full_table_name = f'{table_prefix}"{table_name}"'
        groups: Dict[Tuple[str, ...], List[str]] = {}

        for row in rows:
            if not isinstance(row, dict):
                continue
            
            # Determine which columns to include based on the flag
            if ignore_empty_columns:
                active_cols = sorted([col for col, val in row.items() if val is not None])
            else:
                active_cols = sorted(row.keys())
            
            if not active_cols:
                continue
            
            col_key = tuple(active_cols)
            formatted_vals = []
            
            for col in active_cols:
                val = row.get(col)
                if val is None:
                    formatted_vals.append("NULL")
                elif isinstance(val, str):
                    formatted_vals.append(f"'{val.replace("'", "''")}'")
                else:
                    formatted_vals.append(str(val))
            
            row_values_sql = f"({', '.join(formatted_vals)})"
            groups.setdefault(col_key, []).append(row_values_sql)

        # Construct statements
        for cols, values_list in groups.items():
            col_names_sql = ", ".join([f'"{c}"' for c in cols])
            all_values_sql = ",\n    ".join(values_list)
            insert_statements.append(f"INSERT INTO {full_table_name} ({col_names_sql})\nVALUES\n    {all_values_sql};")

    return insert_statements