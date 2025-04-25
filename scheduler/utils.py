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
        print(f"  Instructions: {bundle['instrs']}")
    print("===========================\n")


def format_instructions_schedule(schedule):
    formatted_schedule = []
    
    for cycle in schedule:
        # Start with 5 "nop" slots
        formatted_cycle = [" nop"] * 5
        
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
                formatted_cycle[0] = line  # Assume ALU
            elif op == "ld":
                line = f" ld {dest}, {mem}"
                formatted_cycle[3] = line  # MEM slot
            elif op == "st":
                line = f" st {dest}, {mem}"
                formatted_cycle[3] = line  # MEM slot
            elif op == "mulu":
                line = f" mulu {dest}, {src1}, {src2}"
                formatted_cycle[1] = line  # MULT slot
            elif op == "loop":
                line = f" loop {dest}"
                formatted_cycle[4] = line  # BRANCH slot
            else:
                line = f" {op} {dest}, {src1}, {src2}"
                formatted_cycle[0] = line  # default to ALU

        formatted_schedule.append(formatted_cycle)

    return formatted_schedule



def sort_instructions_by_unit(schedule):
    def get_unit_priority(opcode):
        if opcode in ['mov', 'addi']:
            return 0  # ALU
        elif opcode in ['mulu', 'mul']:
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
    elif instr["opcode"].startswith("loop") or instr["opcode"].startswith("loop.pip"):
        return "BRANCH"
    return "BB"


def init_bundle():
    return {
        "ALU": 0,
        "MULT": 0,
        "MEM": 0,
        "BRANCH": 0,
        "instrs": []
    }
