"""Fix the SHL catalog JSON file - handle invalid control characters."""

import json
import re

# Read the file
with open('catalog.json', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Replace any literal newlines within quoted strings
# The issue is: "name": "Microsoft \n 365 (New)"
# We need to replace with: "name": "Microsoft \\n 365 (New)"

# More robust: find all string values and escape newlines in them
# Use a state machine approach

def fix_json_strings(text):
    result = []
    in_string = False
    i = 0

    while i < len(text):
        char = text[i]

        if char == '"' and (i == 0 or text[i-1] != '\\'):
            # Toggle string state
            in_string = not in_string
            result.append(char)
        elif in_string and char in ('\n', '\r'):
            # Replace literal newline with escaped version
            if char == '\n':
                result.append('\\n')
            else:
                result.append('\\r')
        else:
            result.append(char)

        i += 1

    return ''.join(result)

# Apply the fix
fixed = fix_json_strings(content)

# Try to load
try:
    data = json.loads(fixed)
    print(f'SUCCESS! Loaded {len(data)} items from SHL catalog')

    # Save fixed version
    with open('catalog.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print('Saved fixed catalog.json')

    # Show a few examples
    print('\nFirst 3 assessments:')
    for item in data[:3]:
        print(f'  - {item.get("name")}')
        print(f'    Type: {item.get("keys", [])}')

except json.JSONDecodeError as e:
    print(f'Failed: {e}')
    print(f'Around position {e.pos}: ...{fixed[e.pos-50:e.pos+50]}...')