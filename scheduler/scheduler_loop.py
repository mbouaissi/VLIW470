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

    bb1_start = next((i for i, instr in enumerate(parsedInstruction) if instr["opcode"] == "BB1"), len(parsedInstruction))
    bb2_start = next((i for i, instr in enumerate(parsedInstruction) if instr["opcode"] == "BB2"), None)

    # Schedule BB0 
    schedule += schedule_basic_block(parsedInstruction[:bb1_start], dependencyTable,unit_limit,parsedInstruction)
    
    if bb1_start is len(parsedInstruction):
        return schedule
    
    # Schedule BB1 
    scheduleBB1 = schedule_bb1(parsedInstruction[bb1_start+1:bb2_start], dependencyTable, unit_limit, parsedInstruction)

    add_delay_BB0_dependency(schedule, scheduleBB1, dependencyTable, parsedInstruction)
            
    scheduleBB2 = schedule_basic_block(parsedInstruction[bb2_start+1:], dependencyTable,unit_limit,parsedInstruction) if bb2_start is not None else []

    return schedule + scheduleBB1 + scheduleBB2

def add_delay_BB0_dependency(schedule, scheduleBB1, dependencyTable, parsedInstruction):
    for idxBB1, instrBB1 in enumerate(scheduleBB1):
        for instBB1 in instrBB1["instrs"]:
            for dep_type in ["loopInvarDep", "interloopDep"]:
                for dep in get_instruction_with_id(dependencyTable,instBB1)[dep_type]:                  
                    # Check if the dependency is in BB0
                    for idxBB0, instrBB0 in enumerate(schedule):
                        for instBB0 in instrBB0["instrs"]:
                            if dep == instBB0:
                                instructionBB0 = get_instruction_with_id(parsedInstruction,instBB0)
                                delay = compute_delay(0, instructionBB0)
                                
                                while delay>compute_relative_distance(idxBB0, idxBB1, schedule):
                                    new_bundle = init_bundle()
                                    schedule.append(new_bundle)


def compute_relative_distance(idxBB0, idxBB1, scheduleBB0):
    dist0 = len(scheduleBB0) - idxBB0
    dist1 =  idxBB1
    print(f"Distance between BB0 and BB1: {dist0} + {dist1}")
    
    return dist0 + dist1

def schedule_basic_block(instructions, dependencyTable, unit_limit, full_instr_list):
    schedule = []
    for instr in instructions:
        global_idx = full_instr_list.index(instr)
        unit = get_unit_type(instr)
        if unit == "BB":
            continue
        
        min_delay = can_schedule_instruction(schedule, dependencyTable, instr, global_idx, full_instr_list)

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

def schedule_bb1(instructions, dependencyTable, unit_limit, full_instr_list):
    schedule = []

    for local_idx, instr in enumerate(instructions):
        global_idx = full_instr_list.index(instr)
        unit = get_unit_type(instr)
        #Schedule the jump as the last instruction, or skip if BB inst
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
        
        
        min_delay = can_schedule_instruction(schedule, dependencyTable, instr, global_idx, full_instr_list)

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

def can_schedule_instruction(schedule, dependencyTable, instr, idx, instructions):
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

    return min_delay

def compute_delay(scheduled_cycle, instr):
    """
    Returns the cycle when the result of an instruction is available.
    """
    unit = get_unit_type(instr)
    latency = 3 if unit == "MULT" else 1
    return scheduled_cycle + latency


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

