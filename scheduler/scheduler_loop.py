from utils import init_bundle, get_unit_type, get_instruction_with_id, unit_limit

def simple_loop(dependencyTable, parsedInstruction):
    """
    Simulates a simple loop scheduler using the 'loop' instruction.
    Schedules BB0, BB1, and BB2 based on dependencies and resource constraints.
    """
    

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

    # Schedule BB2
    add_delay_BB2_dependency( scheduleBB1,scheduleBB2, dependencyTable, parsedInstruction)
    
    return schedule + scheduleBB1 + scheduleBB2

def add_delay_BB0_dependency(scheduleBB0, scheduleBB1, dependencyTable, parsedInstruction):
    for idxBB1, instrBB1 in enumerate(scheduleBB1):
        for instBB1 in instrBB1["instrs"]:
            for dep_type in ["loopInvarDep", "interloopDep"]:
                for dep in get_instruction_with_id(dependencyTable,instBB1)[dep_type]:                  
                    # Check if the dependency is in BB0
                    for idxBB0, instrBB0 in enumerate(scheduleBB0):
                        for instBB0 in instrBB0["instrs"]:
                            if dep == instBB0:
                                instructionBB0 = get_instruction_with_id(parsedInstruction,instBB0)
                                delay = compute_delay(0, instructionBB0)
                                
                                while delay>compute_relative_distance(idxBB0, idxBB1, scheduleBB0):
                                    new_bundle = init_bundle()
                                    scheduleBB0.append(new_bundle)


def add_delay_BB2_dependency( scheduleBB1,scheduleBB2, dependencyTable, parsedInstruction):
    # Check if the dependency is in BB2
    for idxBB2, instrBB2 in enumerate(scheduleBB2):
        for instBB2 in instrBB2["instrs"]:
            for dep_type in ["postLoopDep"]:
                for dep in get_instruction_with_id(dependencyTable,instBB2)[dep_type]:   
                    #If there is, we check which instruction in BB1 is dependent on it
                                   
                    for idxBB1, instrBB1 in enumerate(scheduleBB1):
                        for instBB1 in instrBB1["instrs"]:
                            if dep == instBB1:
                                instructionBB1 = get_instruction_with_id(parsedInstruction,instBB1)
                                delay = compute_delay(0, instructionBB1)
                                #Then we adjust the bubbles accrordingly
                                while delay>compute_relative_distance(idxBB1, idxBB2, scheduleBB1):
                                    new_bundle = init_bundle()
                                    scheduleBB2.insert(0,new_bundle)
                                    idxBB2 += 1
                                    
                                    
def compute_relative_distance(idxBB0, idxBB1, scheduleBB0):
    dist0 = len(scheduleBB0) - idxBB0
    dist1 =  idxBB1
    
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



