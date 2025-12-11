import logging

logger = logging.getLogger(__name__)


def clean_csv_format(file_path):
    """
    Clean CSV format that uses ="value" encapsulation (common in Excel exports).
    Handles both comma-separated and tab-separated files.
    Expects UTF-8 encoded file (converted by import endpoint).
    """
    # Try UTF-8 first (converted by import endpoint), fallback to utf-16le for legacy
    content = None
    encoding_used = None

    for encoding in ["utf-8-sig", "utf-16le"]:
        try:
            with open(file_path, "r", encoding=encoding) as file:
                content = file.read()
                encoding_used = encoding
                break
        except UnicodeError:
            continue

    if content is None:
        raise ValueError(f"Could not read file with supported encodings: {file_path}")

    logger.debug(f"Reading file with encoding: {encoding_used}")
    logger.debug(f"First 200 chars: {repr(content[:200])}")

    # Detect the field delimiter (tab or comma)
    first_line = content.split("\n")[0] if "\n" in content else content

    # Check if tab-delimited (tabs between ="..." fields)
    if (
        '\t="' in first_line
        or '"\t=' in first_line
        or first_line.count("\t") > first_line.count(",")
    ):
        field_delimiter = "\t"
        logger.debug("Detected tab-delimited Excel format")
    else:
        field_delimiter = ","
        logger.debug("Detected comma-delimited Excel format")

    # Strip trailing newlines
    content = content.rstrip("\n")

    # Split into lines
    lines = content.split("\n")

    cleaned_lines = []
    for line in lines:
        # First split by the field delimiter to get individual fields
        if field_delimiter == "\t":
            raw_fields = line.split("\t")
        else:
            # For comma-delimited, we need to handle the ="value" format differently
            # Split on '="' which marks the start of encapsulated fields
            raw_fields = line.split('="')

        cleaned_fields = []
        found_funding_charges = False
        found_trading_adjustment = False

        if field_delimiter == "\t":
            # Tab-delimited: each field is either ="value" or a plain value
            for field in raw_fields:
                field = field.strip()
                # Remove ="..." encapsulation
                if field.startswith('="') and field.endswith('"'):
                    field = field[2:-1]
                elif field.startswith('="'):
                    field = field[2:]
                elif field.endswith('"'):
                    field = field[:-1]

                # Handle empty quoted fields like =""
                if field == "=":
                    field = ""

                cleaned_fields.append(field.strip())

                # Check for funding/adjustment rows that need Amount field
                if field.startswith("Fund"):
                    found_funding_charges = True
                if field.startswith("Trading Adjustment"):
                    found_trading_adjustment = True

            # Insert 0.0 for Amount field if needed (field index 4)
            if (found_funding_charges or found_trading_adjustment) and len(
                cleaned_fields
            ) >= 4:
                if cleaned_fields[4] == "" or cleaned_fields[4] == "0":
                    cleaned_fields[4] = "0.0"
        else:
            # Comma-delimited: original logic for ="value" format
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
                        if current_field.startswith("Fund"):
                            found_funding_charges = True

                        if current_field.startswith("Trading Adjustment"):
                            found_trading_adjustment = True

                        # If this is the Description field (comes right after Action)
                        # and we found Funding Charges, add the '0'
                        if found_funding_charges and len(cleaned_fields) == 4:
                            cleaned_fields.append("0.0")
                            found_funding_charges = False
                        if found_trading_adjustment and len(cleaned_fields) == 4:
                            cleaned_fields.append("0.0")
                            found_trading_adjustment = False
                        else:
                            # Add any remaining numeric fields
                            remaining = parts[1].strip()
                            if remaining:
                                numeric_fields = [
                                    f.strip() for f in remaining.split() if f.strip()
                                ]
                                cleaned_fields.extend(numeric_fields)

        cleaned_line = ",".join(cleaned_fields)
        cleaned_lines.append(cleaned_line)

    # Remove the first comma from the first line (if it starts with comma)
    if cleaned_lines and cleaned_lines[0].startswith(","):
        cleaned_lines[0] = cleaned_lines[0][1:]

    temp_file = file_path + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        file.write("\n".join(cleaned_lines))

    logger.debug(
        f"Cleaned file first line: {cleaned_lines[0] if cleaned_lines else 'empty'}"
    )

    return temp_file


def detect_file_format(file_path):
    """
    Detect if file is in Windows format (="Column") or standard CSV format.
    Expects UTF-8 encoded file (converted by import endpoint).
    """
    content = None

    # Try UTF-8-sig first (handles BOM), fallback to utf-16le for legacy
    for encoding in ["utf-8-sig", "utf-16le"]:
        try:
            with open(file_path, "r", encoding=encoding) as file:
                first_line = file.readline()
                content = first_line
                break
        except UnicodeError:
            continue

    if content is None:
        logger.warning(f"Could not read file to detect format: {file_path}")
        return "unknown"

    # Check for Windows Excel format with ="value" encapsulation
    if '="' in content:
        return "windows"

    # Standard CSV format
    if "," in content:
        return "standard"

    # Tab-separated
    if "\t" in content:
        return "standard"

    return "unknown"
