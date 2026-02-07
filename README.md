# JSON Mapper

A Python utility for transforming and mapping JSON files based on predefined mapping configurations.

## Overview

JSON Mapper reads JSON input files, applies transformation rules defined in mapping configuration files, and outputs the transformed JSON to a designated output directory. It supports complex nested structures, flattening arrays, and conditional filtering.

## Project Structure

```
json_to_json_mapper/
├── json_mapper.py              # Main entry point
├── mapping_functions.py        # Core mapping logic
├── json_input/                 # Input JSON files directory
├── json_mappings/              # Mapping configuration files
├── json_output/                # Output transformed JSON files
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── LICENSE                     # License information
└── .gitignore                  # Git ignore rules
```

## Features

- **Batch Processing**: Process multiple JSON files in a single run
- **Flexible Mapping**: Define custom mappings for complex transformations
- **Filtering**: Conditionally apply mappings based on filter criteria
- **Array Flattening**: Flatten nested arrays into separate output records
- **Error Handling**: Graceful error handling and detailed error reporting
- **Type Validation**: Support for multiple data types with validation

## Requirements

- Python 3.8+
- Standard library modules: `json`, `os`, `re`, `hashlib`

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd json_to_json_mapper
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies (if any):
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start

1. Place your JSON input files in the `json_input/` directory
2. Create or update mapping configuration files in `json_mappings/` 
3. Run the mapper:
   ```bash
   python json_mapper.py
   ```
4. Check the `json_output/` directory for transformed files

### Mapping Configuration

Create a JSON mapping file in `json_mappings/` with the following structure:

```json
{
  "filter": [
    {
      "attribute": "order_header.order_status",
      "value": "CREATED"
    }
  ],
  "mapping": [
    {
      "table_name": "order_header",
      "columns": [
        {
          "name": "order_id",
          "datatype": "VARCHAR",
          "mapping": "order_header.order_id"
        },
        {
          "name": "order_date",
          "datatype": "TIMESTAMP",
          "mapping": "order_header.order_date"
        }
      ]
    },
    {
      "table_name": "order_items",
      "flatten": "order_items",
      "columns": [
        {
          "name": "item_sku",
          "datatype": "VARCHAR",
          "mapping": "sku"
        }
      ]
    }
  ]
}
```

### Configuration Sections

- **filter**: Conditions that must match for the mapping to apply
  - `attribute`: Path to the attribute in input JSON (dot notation)
  - `value`: Regex pattern to match against the attribute value

- **mapping**: Array of table mappings
  - `table_name`: Name of the output table/object
  - `flatten` (optional): Path to array to flatten into separate records
  - `columns`: Array of column definitions
    - `name`: Output column name
    - `datatype`: Data type (VARCHAR, INT, DECIMAL, TIMESTAMP, etc.)
    - `mapping`: Path to source attribute in input JSON

## Error Handling

The mapper gracefully handles:
- Missing filter attributes (skips mapping instead of throwing error)
- Missing source attributes (uses default values)
- Invalid mapping configurations (validates and reports)
- Type mismatches (checks datatype compatibility)

## File Naming

- Input files: Place raw JSON files in `json_input/`
- Output files: Generated files in `json_output/` keep the same filename
- Mapping files: Use descriptive names like `mapping_1.json`, `mapping_orders.json`

## Example

**Input** (`json_input/order.json`):
```json
{
  "order_header": {
    "order_id": "ORD-001",
    "order_status": "CREATED"
  }
}
```

**Mapping** (`json_mappings/mapping_1.json`):
```json
{
  "filter": [{"attribute": "order_header.order_status", "value": "CREATED"}],
  "mapping": [{
    "table_name": "orders",
    "columns": [{"name": "id", "datatype": "VARCHAR", "mapping": "order_header.order_id"}]
  }]
}
```

**Output** (`json_output/order.json`):
```json
{
  "orders": [{"id": "ORD-001"}]
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or suggestions, please open an issue in the repository.
