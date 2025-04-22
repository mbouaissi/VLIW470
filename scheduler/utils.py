import re

def parse_mem_operand(operand):
    """
    Parses memory operand like '0(x2)' into {'base': 'x2', 'offset': 0}
    If not a memory operand, returns None
    """
    if operand is None:
        return None
    match = re.match(r"(-?\d+)\((x\d+)\)", operand)
    if match:
        offset, base = match.groups()
        return {"base": base, "offset": int(offset), "raw": operand}
    return None
