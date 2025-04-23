def simple_loop(dependencyTable, parsedInstruction, nbrAlu=2, nbrMult=1, nbrMem=1, nbrBranch=1, delay=1, delayMult=3):
    """
    Simulates a simple loop scheduler using the 'loop' instruction.
    Schedules BB0, BB1, and BB2 based on dependencies and resource constraints.
    """
    unit_limit = {
        "ALU": nbrAlu,
        "MULT": nbrMult,
        "MEM": nbrMem,
        "BRANCH": nbrBranch
    }

    schedule = []
    scheduleBB1 = []
    scheduleBB2 = []

    # Detect where BB1 and BB2 start
    bb1_start = next((i for i, instr in enumerate(parsedInstruction) if instr["opcode"] == "BB1"), None)
    bb2_start = next((i for i, instr in enumerate(parsedInstruction) if instr["opcode"] == "BB2"), None)

    if bb1_start is None:
        return []

    # Schedule BB0 (before BB1)
    schedule += schedule_basic_block(parsedInstruction[:bb1_start], unit_limit)

    # Schedule BB1 (loop body) with dependency-based ASAP
    scheduleBB1 = schedule_bb1(parsedInstruction[bb1_start+1:bb2_start], dependencyTable, unit_limit, parsedInstruction)

    # Schedule BB2 (after BB1)
    scheduleBB2 = schedule_basic_block(parsedInstruction[bb2_start+1:], unit_limit) if bb2_start is not None else []

    return schedule + scheduleBB1 + scheduleBB2


def schedule_basic_block(instructions, unit_limit):
    schedule = []
    for instr in instructions:
        unit = get_unit_type(instr)
        if unit == "BB":
            continue
        
        placed = False
        for bundle in schedule:
            if bundle[unit] < unit_limit[unit]:
                bundle[unit] += 1
                bundle["instrs"].append(instr["instrAddress"])
                placed = True
                break

        if not placed:
            new_bundle = init_bundle()
            new_bundle[unit] += 1
            new_bundle["instrs"].append(instr["instrAddress"])
            schedule.append(new_bundle)

    return schedule

def schedule_bb1(instructions, dependencyTable, unit_limit, full_instr_list):
    schedule = []

    for local_idx, instr in enumerate(instructions):
        global_idx = full_instr_list.index(instr)
        unit = get_unit_type(instr)
        if unit == "BB":
            continue
        elif unit == "BRANCH":
            bundle = schedule[-1]
            if bundle[unit] < unit_limit[unit]:
                bundle[unit] += 1
                bundle["instrs"].append(instr["instrAddress"])
            else:
                new_bundle = init_bundle()
                new_bundle[unit] += 1
                new_bundle["instrs"].append(instr["instrAddress"])
                schedule.append(new_bundle)
            continue
        min_delay = can_schedule_instruction(schedule, dependencyTable, unit, instr, global_idx, full_instr_list)

        scheduled = False
        
        while len(schedule) <= min_delay:
            schedule.append(init_bundle())
            
        scheduled = False
        for i in range(min_delay, len(schedule)):
            if schedule[i][unit] < unit_limit[unit]:
                schedule[i][unit] += 1
                schedule[i]["instrs"].append(instr["instrAddress"])
                scheduled = True
                break

        if not scheduled:
            new_bundle = init_bundle()
            new_bundle[unit] += 1
            new_bundle["instrs"].append(instr["instrAddress"])
            schedule.append(new_bundle)
    return schedule

def can_schedule_instruction(schedule, dependencyTable, unit, instr, idx, instructions):
    """
    Computes the earliest cycle an instruction can be scheduled at,
    based on its dependencies and instruction latency.
    """
    dependency = dependencyTable[idx]
    print(f"Checking dependencies for instruction {instr['instrAddress']}: {dependency}")
    
    min_delay = 0
    # Check each type of dependency
    for dep_type in ["localDependency", "loopInvarDep", "postLoopDep", "interloopDep"]:
        for dep in dependency[dep_type]:
            for i in range(len(schedule)):
                if dep in schedule[i]["instrs"]:
                    delay = compute_delay(i, get_instruction_with_id(instructions,dep))  # pass instr directly
                    min_delay = max(min_delay, delay)
                    print(f"Dependency {dep} found in cycle {i}")
                    
    print(f"Minimum delay for instruction {instr['instrAddress']} is {min_delay}")
    return min_delay

def compute_delay(scheduled_cycle, instr):
    """
    Returns the cycle when the result of an instruction is available.
    """
    print(f"Computing delay for instruction {instr} at cycle {scheduled_cycle}")
    unit = get_unit_type(instr)
    latency = 3 if unit == "MULT" else 1
    return scheduled_cycle + latency


def add_instruction_to_schedule(schedule, instruction, index):
    """
    Adds an instruction to the schedule at the specified index.
    """
    ensure_bundle_exists(schedule, index)
    schedule[index].append(instruction)
    
def ensure_bundle_exists(schedule, index):
    while len(schedule) <= index:
        schedule.append([])

def get_instruction_with_id(parsed_instruction, instr_id):
    """
    Returns the instruction with the specified ID from the parsed instructions.
    """
    for instr in parsed_instruction:
        if instr["instrAddress"] == instr_id:
            return instr
    return None

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

