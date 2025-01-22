import logging

logger = logging.getLogger(__name__)

def clean_csv_format(file_path):
    with open(file_path, 'r', encoding='utf-16le') as file:
        content = file.read()
    
    # Print content end for verification
    print(f"Last few characters before cleaning: {repr(content[-10:])}")
    
    # Remove tab characters and newlines
    content = content.replace('\t', ' ').rstrip('\n')
    print(f"Last few characters after cleaning: {repr(content[-10:])}")

    # Split into lines
    lines = content.split('\n')
    
    cleaned_lines = []
    for line in lines:        # Split on '="' which marks the start of encapsulated fields
        raw_fields = line.split('="')
        cleaned_fields = []
        found_funding_charges = False  # Track if we found Funding Charges in this line

        for i, field in enumerate(raw_fields):
            if i == 0:
                # First field - remove leading '="' if present
                field = field.lstrip('="')
                if field:
                    cleaned_fields.append(field.strip())
            else:
                # Find where the encapsulated field ends (next quote)
                parts = field.split('"')
                if len(parts) >= 2:
                    # Add the encapsulated part
                    current_field = parts[0].strip()
                    cleaned_fields.append(current_field)
                    
                    # Set flag if this is Funding Charges
                    #if current_field == 'Funding Charges':
                    if current_field.startswith('Fund'):
                        found_funding_charges = True
                    
                    # If this is the Description field (comes right after Action)
                    # and we found Funding Charges, add the '0'
                    if found_funding_charges and len(cleaned_fields) == 4:
                        cleaned_fields.append('0.0')
                        found_funding_charges = False  # Reset the flag
                    else:
                        # Add any remaining numeric fields
                        remaining = parts[1].strip()
                        if remaining:
                            numeric_fields = [f.strip() for f in remaining.split() if f.strip()]
                            cleaned_fields.extend(numeric_fields)
        cleaned_line = ','.join(cleaned_fields)
        cleaned_lines.append(cleaned_line)
        #print(f"Cleaned line: '{cleaned_line}'")

#    print(f"LAST Cleaned lines: {cleaned_lines[-1]}") 

    # Remove the first comma from the first line
    cleaned_lines[0] = cleaned_lines[0].replace(',', '', 1)
    temp_file = file_path + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(cleaned_lines))
    
    return temp_file

def detect_file_format(file_path):
    """Detect if file is in Windows format (="Column") or Mac format (standard CSV)"""
    try:
        # Try reading first line with utf-16le (Windows format)
        with open(file_path, 'r', encoding='utf-16le') as file:
            first_line = file.readline()
            if '="' in first_line:
                return 'windows'
    except UnicodeError:
        pass
    
    # Try reading as standard CSV (Mac format)
    try:
        with open(file_path, 'r', encoding='utf-16le') as file:
            first_line = file.readline()
            if ',' in first_line and '="' not in first_line:
                return 'mac'
    except UnicodeError:
        pass
    
    return 'unknown'
