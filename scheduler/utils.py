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
def format_instructions_schedule(schedule):
    formatted_schedule = []
    
    for cycle in schedule:
        # Start with 5 "nop" slots
        formatted_cycle = ["nop"] * 5
        
        for instr in cycle:
            op = instr['opcode']
            dest = instr.get('dest')
            src1 = instr.get('src1')
            src2 = instr.get('src2')
            mem = instr.get('memSrc1')

            if op == "mov":
                line = f" mov {dest}, {src1}"
                formatted_cycle[cycle.index(instr)] = line
            elif op == "addi":
                line = f" addi {dest}, {src1}, {src2}"
                formatted_cycle[0] = line  # ALU
            elif op == "ld":
                line = f" ld {dest}, {mem}"
                formatted_cycle[3] = line  # MEM
            elif op == "st":
                line = f" st {dest}, {mem}"
                formatted_cycle[3] = line  # MEM
            elif op == "mulu":
                line = f" mulu {dest}, {src1}, {src2}"
                formatted_cycle[1] = line  # MULT
            elif op == "loop":
                line = f" loop {dest}"
                formatted_cycle[4] = line  # BRANCH
            else:
                line = f" {op} {dest}, {src1}, {src2}"
                formatted_cycle[0] = line  # default to ALU (sub + add)

        formatted_schedule.append(formatted_cycle)

    return formatted_schedule


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


def convert_loop_to_json(parsedInstruction, schedule):
    """
    Converts the loop schedule to a JSON format,
    enforcing specific slots:
    Slot 0-1: ALU, Slot 2: MULT, Slot 3: MEM, Slot 4: BRANCH
    """
    json_schedule = []
    
    instr_map = {instr["instrAddress"]: instr for instr in parsedInstruction if instr["instrAddress"] != -1}

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
                # for idx, bundle2 in enumerate(schedule):
                #     for i in bundle2["instructions"]:
                #         i = instr_map.get(i)
                #         if i["instrAddress"] == int(instr["dest"]):
                #             instr["dest"] = idx
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

def format_instruction(instr):
    opcode = instr["opcode"]
    dest = instr.get("dest")
    src1 = instr.get("src1")
    src2 = instr.get("src2")
    mem = instr.get("memSrc1")
    
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