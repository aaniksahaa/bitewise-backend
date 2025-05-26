import re
import json 

def extract_json_block(s: str) -> str:
    start = s.find("```json")
    if start == -1:
        start = s.find("```")  # Fallback to plain code block
    end = s.find("```", start + 7 if "json" in s[start:start+7] else start + 3)
    if start != -1 and end != -1:
        return s[start + (7 if "json" in s[start:start+7] else 3):end].strip()
    if start != -1 and end == -1:
        raise ValueError("Unclosed JSON block")
    return s

def parse_json_from_output(text):
    json_text = extract_json_block(text)
    
    # Remove control characters
    json_text = re.sub(r'[\x00-\x1F\x7F]', '', json_text)
    # Remove invalid escape sequences
    json_text = re.sub(r'\\(?!["\\/bfnrtu])', '', json_text)
    json_text = re.sub(r'\\u[0-9A-Fa-f]{0,3}(?![0-9A-Fa-f])', '', json_text)
    
    try:
        data = json.loads(json_text)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")