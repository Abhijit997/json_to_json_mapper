import mapping_functions
import json
import os

if __name__ == "__main__":
    local_mappings_path = 'json_mappings/'
    local_input_path = 'json_input/'
    local_output_path = 'json_output/'

    # Load mapping
    with open('json_mappings/mapping_1.json') as f:
        mapping_dict = json.load(f)

    # Loop through each JSON file in input directory
    for filename in os.listdir(local_input_path):
        if filename.endswith('.json'):
            input_file_path = os.path.join(local_input_path, filename)
            
            with open(input_file_path) as f:
                payload_dict = json.load(f)
            
                mapped_tables = mapping_functions.process_mappings_local(payload_dict, local_mappings_path)
            
                # Save output
                output_file_path = os.path.join(local_output_path, filename)
                with open(output_file_path, 'w') as f:
                    json.dump(mapped_tables, f, indent=2)
            
            print(f"Processed: {input_file_path} -> {output_file_path}")