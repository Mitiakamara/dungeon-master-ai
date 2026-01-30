
import json
import os

def fix_file(filename):
    if not os.path.exists(filename):
        print(f"{filename} not found.")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cleaned_data = []
    
    # Check if this is the "Bad" structure (list of dicts with 'text' key containing JSON string)
    for entry in data:
        if isinstance(entry, dict) and "text" in entry:
            # It's wrapped!
            try:
                inner_json = entry["text"]
                # Sometimes it might be empty like "[]"
                if not inner_json or inner_json == "[]":
                    continue
                    
                parsed_inner = json.loads(inner_json)
                if isinstance(parsed_inner, list):
                    cleaned_data.extend(parsed_inner)
                elif isinstance(parsed_inner, dict):
                    cleaned_data.append(parsed_inner)
            except Exception as e:
                print(f"Error parsing inner JSON in {filename}: {e}")
        else:
            # It's seemingly normal?
            cleaned_data.append(entry)

    print(f"Fixed {filename}: Converted {len(data)} wrappers into {len(cleaned_data)} real objects.")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    fix_file("monsters_data.json")
    fix_file("items_data.json")
