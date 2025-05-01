import re
import struct

def parse_mem_operand(operand):
    """
    Parses memory operand like '0(x2)' or '0x1000(x2)' into {'base': 'x2', 'offset': 0 or 4096}
    """
    if operand is None:
        return None
    match = re.match(r"(-?(?:0x)?[0-9a-fA-F]+)\((x\d+)\)", operand)
    if match:
        offset_str, base = match.groups()
        if offset_str.startswith('0x') or offset_str.startswith('-0x'):
            offset = int(offset_str, 16)
        else:
            offset = int(offset_str, 10)
        return {"base": base, "offset": offset, "raw": operand}
    return None


def get_instruction_with_id(parsed_instruction, instr_id):
    """
    Returns the instruction with the specified ID from the parsed instructions.
    """
    for instr in parsed_instruction:
        if instr["instrAddress"] == instr_id:
            return instr
    return None

def print_schedule(schedule):
    print("\n=== Simple Loop Schedule ===")
    for cycle, bundle in enumerate(schedule):
        print(f"Cycle {cycle}:")
        for unit in ["ALU", "MULT", "MEM", "BRANCH"]:
            count = bundle[unit]
            print(f"  {unit:<6}: {count} slot(s)")
        print(f"  Instructions: {bundle['instructions']}")
    print("===========================\n")

# XXX: nothing to FU 2 (shouldn't mulu go to 2)?
# Try to regroup the instructions per slot type
# Too simplistic as may overwrite?



def sort_instructions_by_unit(schedule):
    def get_unit_priority(opcode):
        if opcode in ['mov', 'addi', 'add', 'sub']:
            return 0  # ALU
        elif opcode in ['mulu']:
            return 1  # MULT
        elif opcode in ['ld', 'st']:
            return 2  # MEM
        elif opcode in ['loop']:
            return 3  # BRANCH
        return 4  

    sorted_schedule = []
    for cycle in schedule:
        sorted_cycle = sorted(cycle, key=lambda instr: get_unit_priority(instr['opcode']))
        sorted_schedule.append(sorted_cycle)
    
    return sorted_schedule


def get_unit_type(instr):
    if instr["opcode"] in ["add", "addi", "sub", "mov"]:
        return "ALU"
    elif instr["opcode"] == "mulu":
        return "MULT"
    elif instr["opcode"] in ["ld", "st"]:
        return "MEM"
    elif instr["opcode"] in ["loop", "loop.pip"]:
        return "BRANCH"
    return "BB"

def shift_instr_addresses(schedule, from_instr_address, shift_by):
    for bundle in schedule:
        for instr in bundle:
            if instr["instrAddress"] and instr["instrAddress"] >= from_instr_address:
                instr["instrAddress"] += shift_by
                
def compute_delay(scheduled_cycle, instr):
    """
    Returns the cycle when the result of an instruction is available.
    """
    unit = get_unit_type(instr)
    latency = 3 if unit == "MULT" else 1
    return scheduled_cycle + latency       


def convert_loop_to_json(instructions, schedule):
    """
    Converts the loop schedule to a JSON format,
    enforcing specific slots:
    Slot 0-1: ALU, Slot 2: MULT, Slot 3: MEM, Slot 4: BRANCH
    """
    json_schedule = []
    
    instr_map = {instr["instrAddress"]: instr for instr in instructions if instr["instrAddress"] != -1}

    for bundle in schedule:
        slots = [" nop"] * 5  # Initialize with 5 nops
        # classify instructions
        alus = []
        mults = []
        mems = []
        branch = []
        
        for addr in bundle["instructions"]:
            instr = instr_map.get(addr)
            if instr is None:
                continue
            opcode = instr["opcode"]
            if opcode in ["mov", "add", "addi", "sub"]:
                alus.append(instr)
            elif opcode in ["mulu"]:
                mults.append(instr)
            elif opcode in ["ld", "st"]:
                mems.append(instr)
            elif opcode == "loop":
                branch.append(instr)

        # fill slots
        if len(alus) > 0:
            slots[0] = format_instruction(alus[0])
        if len(alus) > 1:
            slots[1] = format_instruction(alus[1])
        if len(mults) > 0:
            slots[2] = format_instruction(mults[0])
        if len(mems) > 0:
            slots[3] = format_instruction(mems[0])
        if len(branch) > 0:
            slots[4] = format_instruction(branch[0])

        json_schedule.append(slots)

    return json_schedule

def format_operand(op):
    if op is None:
        return None
    if isinstance(op, str):
        # Check if it's a memory operand first
        
        mem_match = re.match(r"(-?0x[0-9a-fA-F]+)\((x\d+)\)", op)
        if mem_match:
            offset_hex, base_reg = mem_match.groups()
            offset_dec = str(int(offset_hex, 16))
            return f"{offset_dec}({base_reg})"
        elif op.startswith("0x"):
            return str(int(op, 16))
    return op

def format_instruction(instr):
    opcode = instr["opcode"]
    dest = instr.get("dest")
    src1 = format_operand(instr.get("src1"))
    src2 = format_operand(instr.get("src2"))
    mem = format_operand(instr.get("memSrc1"))
    print(instr)

    if opcode == "loop":
        return f" {opcode} {dest}"
    elif opcode in ["ld", "st"] and mem:
        return f" {opcode} {dest}, {mem}"
    elif src2:
        return f" {opcode} {dest}, {src1}, {src2}"
    elif src1:
        return f" {opcode} {dest}, {src1}"
    else:
        return f" {opcode} {dest}"



def empty_block(name):
    return {"instrAddress": -1, "opcode": name, "dest": None, "src1": None, "src2": None, "memSrc1": None, "memSrc2": None}


def init_bundle():
    return {
        "ALU": 0,
        "MULT": 0,
        "MEM": 0,
        "BRANCH": 0,
        "instructions": []
    }

unit_limit = {
        "ALU": 2,
        "MULT": 1,
        "MEM": 1,
        "BRANCH": 1
    }

priority = {'ALU': 0, 'MULT': 1, 'MEM': 2, 'BRANCH': 3}

def count_operations_per_class(instructions):
    """
    Counts the number of operations of each unit type in the given instruction list.
    
    Args:
        instructions (list): List of parsed instruction dictionaries.
    
    Returns:
        dict: Mapping from unit type (e.g., "ALU", "MEM") to number of operations.
    """
    counts = {}
    for instr in instructions:
        unit = get_unit_type(instr)
        if unit == "BB":
            continue
        if unit not in counts:
            counts[unit] = 0
        counts[unit] += 1
    return counts

def find_bundle_of_instr(instr_address, schedule):
    """Finds the bundle index where an instruction is placed."""
    for idx, bundle in enumerate(schedule):
        if instr_address in bundle['instructions']:
            return idx
    return None  # Not found

# For debugging purposes
def print_schedule(schedule):
    for idx, bundle in enumerate(schedule):
        print(f"Bundle {idx}: {bundle}")

def extract_reg_from_mem(mem_string):
    if not mem_string or '(' not in mem_string or ')' not in mem_string:
        return None
    return mem_string[mem_string.find('(')+1 : mem_string.find(')')]



def clean_instructions(instructions):

    def resolve_register_offset(reg_str):
        match = re.match(r"x(\d+)\(\+(\d+),\+(\d+)\)", reg_str)
        if not match:
            return reg_str
        base = int(match.group(1))
        iter_offset = int(match.group(2))
        stage_offset = int(match.group(3))
        total = base + iter_offset + stage_offset
        return f"x{total}"

    def resolve_fields(instr):
        for field in ['dest', 'src1', 'src2']:
            val = instr.get(field)
            if val:
                resolved = resolve_register_offset(val)
                if resolved != val:
                    print(f"[RegFix] {field}: {val} → {resolved}")
                instr[field] = resolved

        for mem_field in ['memSrc1', 'memSrc2']:
            val = instr.get(mem_field)
            if not val:
                continue
            # Cherche un registre avec offset dans ()
            match = re.search(r"\((x\d+\(\+\d+,\+\d+\))\)", val)
            if match:
                reg = match.group(1)
                resolved = resolve_register_offset(reg)
                updated = val.replace(reg, resolved)
                if updated != val:
                    print(f"[RegFix] {mem_field}: {val} → {updated}")
                instr[mem_field] = updated

    for instr in instructions:
        resolve_fields(instr)

def form_json(instructions, schedule):
    """
    Convertit les bundles du schedule en lignes formatées proprement.
    Slots : [ALU0, ALU1, MULT, MEM, BRANCH]
    """
    instr_map = {instr["instrAddress"]: instr for instr in instructions if instr["instrAddress"] != -1}
    json_schedule = []

    def format_instr(instr):
        if not instr:
            return " nop"

        opcode = instr["opcode"]
        dest = instr.get("dest", "")
        src1 = instr.get("src1", "")
        src2 = instr.get("src2", "")
        mem1 = instr.get("memSrc1", "")
        pred = instr.get("predicate", None)

        prefix = f"({pred}) " if pred else ""

        if opcode == "ld":
            return f"{prefix}{opcode} {dest}, {mem1}"
        elif opcode == "st":
            return f"{prefix}{opcode} {dest}, {mem1}"
        elif opcode in ["add", "sub", "mulu", "addi"]:
            return f"{prefix}{opcode} {dest}, {src1}, {src2}"
        elif opcode == "mov":
            return f"{prefix}{opcode} {dest}, {src1}"
        elif opcode == "loop":
            return f"{prefix}loop.pip {dest}"
        else:
            return f"{prefix}{opcode} {dest}, {src1}, {src2}"

    for bundle in schedule:
        slots = [" nop"] * 5

        instrs = [instr_map.get(i) for i in bundle["instructions"] if i in instr_map]

        # Classify
        alus = [i for i in instrs if i["opcode"] in ["mov", "add", "sub", "addi"]]
        mults = [i for i in instrs if i["opcode"] in ["mulu"]]
        mems = [i for i in instrs if i["opcode"] in ["ld", "st"]]
        branch = [i for i in instrs if i["opcode"] == "loop"]

        # Fill slots
        if len(alus) > 0:
            slots[0] = format_instr(alus[0])
        if len(alus) > 1:
            slots[1] = format_instr(alus[1])
        if len(mults) > 0:
            slots[2] = format_instr(mults[0])
        if len(mems) > 0:
            slots[3] = format_instr(mems[0])
        if len(branch) > 0:
            slots[4] = format_instr(branch[0])

        json_schedule.append(slots)

    return json_schedule
