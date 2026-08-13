import re


def duplicate_name(name, existing_names):
    """
    Erzeugt einen freien Namen für eine Kopie.

    Beispiele:
        "Blau"    -> "Blau 2"
        "Blau 2"  -> "Blau 3"
        "Blau 23" -> "Blau 24"
        "Test 99" -> "Test 100"
    """

    existing_names = set(existing_names)

    match = re.match(r"^(.*?)(?:\s+(\d+))?$", name.strip())

    if not match:
        base = name.strip()
        number = None
    else:
        base = match.group(1).strip()
        number = match.group(2)

    if number is not None:
        number = int(number)
        candidate = f"{base} {number + 1}"
    else:
        candidate = f"{base} 2"

    while candidate in existing_names:

        match = re.match(r"^(.*)\s+(\d+)$", candidate)

        if match:
            base = match.group(1)
            number = int(match.group(2)) + 1

            candidate = f"{base} {number}"

        else:
            candidate = f"{candidate} 2"

    return candidate