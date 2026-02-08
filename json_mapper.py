import mapping_functions
import json
import os

if __name__ == "__main__":
    local_mappings_path = 'json_mappings/'
    local_input_path = 'json_input/'
    local_output_path = 'json_output/'
    sql_output_path = 'sql_output/'

    # Loop through each mapping file
    for mapping_filename in os.listdir(local_mappings_path):
        if mapping_filename.endswith('.json'):
            
            # Loop through each JSON file in input directory
            for filename in os.listdir(local_input_path):
                if filename.endswith('.json'):
                    input_file_path = os.path.join(local_input_path, filename)
                    
                    with open(input_file_path) as f:
                        payload_dict = json.load(f)
                    
                        mapped_tables = mapping_functions.process_mappings_local(payload_dict, local_mappings_path)
                    
                        # Save output
                        base_name = filename.replace('.json', '')
                        output_filename = f"{base_name}_{mapping_filename.replace('.json', '')}.json"
                        output_file_path = os.path.join(local_output_path, output_filename)
                        with open(output_file_path, 'w') as f:
                            json.dump(mapped_tables, f, indent=2)
                    
                    sql_filename = f"{base_name}_{mapping_filename.replace('.json', '')}.sql"
                    with open(os.path.join(sql_output_path, sql_filename), 'w') as f:
                        insert_statements = mapping_functions.generate_insert_sql(mapped_tables, catalog='my_catalog', schema='my_schema')
                        for stmt in insert_statements:
                            f.write(stmt + '\n')
                    
                    print(f"Processed: {input_file_path} with {mapping_filename} -> {output_file_path}")