import json
import re

def sanitize_firebase_keys(data):
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            k_str = str(k)
            # Replace forbidden characters for Firebase RTDB keys: . # $ [ ]
            safe_key = re.sub(r'[\.\#\$\[\]]', '_', k_str)
            if safe_key == "":
                safe_key = "empty_key"
            new_dict[safe_key] = sanitize_firebase_keys(v)
        return new_dict
    elif isinstance(data, list):
        return [sanitize_firebase_keys(item) for item in data]
    else:
        return data

def test_db_payload():
    try:
        with open("bgz_local_database.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No local database found.")
        return

    # Check for invalid keys in the raw data
    raw_json = json.dumps(data)
    invalid_chars = ['.', '#', '$', '[', ']']
    found = False
    
    # We can't simply check raw_json because values CAN have these characters. 
    # Only keys are restricted.
    
    sanitized_data = sanitize_firebase_keys(data)
    print("Sanitization complete.")
    
    # Print the sanitized structure size
    print(f"Data size: {len(json.dumps(sanitized_data))} bytes")

if __name__ == "__main__":
    test_db_payload()
