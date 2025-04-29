from utils import *

def pip_loop(dependencyTable, instructions):
    """
    Simulates a loop pipelined (loop.pip) scheduler.
    
    Args:
        dependencyTable (dict).
        instructions (list).
    
    Returns:
        list: List of scheduled instructions across BB0, BB1, and BB2.
    """
    
    scheduleBB0 = []
    scheduleBB1 = []
    scheduleBB2 = []

    bb1_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB1"), len(instructions))
    bb2_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB2"), None)

    # Schedule BB0 
    scheduleBB0 = schedule_non_loop(instructions[:bb1_start], dependencyTable, unit_limit, instructions)
    
    if bb1_start == len(instructions):
        return scheduleBB0
    
    # Schedule BB1 
    scheduleBB1 = schedule_loop(instructions[bb1_start+1:bb2_start], dependencyTable, unit_limit)
    add_delay_BB0_dependency(scheduleBB0, scheduleBB1, dependencyTable, instructions)
    
    # Schedule BB2 
    scheduleBB2 = schedule_non_loop(instructions[bb2_start+1:], dependencyTable, unit_limit, instructions) if bb2_start else []
    add_delay_BB2_dependency(scheduleBB1,scheduleBB2, dependencyTable, instructions)
    
    return scheduleBB0 + scheduleBB1 + scheduleBB2


def schedule_non_loop(block_instr, dependencyTable, unit_limit, full_instr):
    """
    Schedules instructions of a non-loop block based on resource availability and dependencies.
    
    Args:
        block_instr (list): List of instructions belonging to the basic block to be scheduled.
        dependencyTable (dict).
        unit_limit (dict).
        full_instr (list): Complete list of all parsed instructions (to resolve global indices).
    
    Returns:
        list: List of scheduled bundles for non-loop body.
    """
    schedule = []
    for instr in block_instr:
        global_idx = full_instr.index(instr)
        unit = get_unit_type(instr)
        if unit == "BB":
            continue
        
        min_delay = can_schedule_instruction(schedule, dependencyTable, global_idx, full_instr)
        
        while len(schedule) <= min_delay:
            schedule.append(init_bundle())
            
        scheduled = False
        for i in range(min_delay, len(schedule)):
            if schedule[i][unit] < unit_limit[unit]:
                schedule[i][unit] += 1
                schedule[i]["instructions"].append(instr["instrAddress"])
                scheduled = True
                break

        if not scheduled:
            new_bundle = init_bundle()
            new_bundle[unit] += 1
            new_bundle["instructions"].append(instr["instrAddress"])
            schedule.append(new_bundle)
            
    return schedule

def schedule_loop(block_instr, dependencyTable, unit_limit):
    """
    Schedules instructions of a loop block based on "loop.pip" instruction based on resource availability and dependencies.
    
    Args:
        loop_instr (list): List of instructions belonging to the loop block to be scheduled.
        dependency_table (dict).
        unit_limit (dict)..
        full_instr (list): Complete list of all parsed instructions (to resolve global indices).
    
    Returns:
        list: List of scheduled bundles for the loop body.
    """
    II = bounded_ii(block_instr)

    # Create II bundles
    schedule = [init_bundle() for _ in range(int(II)+3)]
    
    for instr in block_instr[:-1]:
        op_class = get_unit_type(instr)

        # Find the matching dependency
        matching_dep = None
        for dep in dependencyTable:
            if dep['instrAddress'] == instr['instrAddress']:
                matching_dep = dep
                break  
        
        latency = 0

        for i in range(int(II)+3):
            if latency > 0:
                latency -= 1
                continue
            

            if schedule[i][op_class] < unit_limit[op_class]: # Ensure resource available

                conflict = False
                if matching_dep:  # Ensure no dependency issue
                    for dep_type in ["localDependency", "interloopDep"]:
                        for (dep_instr_addr, _) in matching_dep[dep_type]:
                            if dep_instr_addr in schedule[i]['instructions']:
                                for guess in block_instr:
                                    if guess['instrAddress'] == dep_instr_addr:
                                        if guess['opcode'] == "mulu":
                                            latency += 2
                                        break

                                conflict = True
                                break


                if conflict:
                    continue  # Conflict detected, try next cycle

                # Update schedule
                schedule[i]['instructions'].append(instr['instrAddress']) 
                schedule[i][op_class] += 1 
                break  # Done scheduling this instruction
            else:
                continue # Not enough resources, try next cycle

    # Add branch to the end of the schedule     
    schedule[-1]['instructions'].append(block_instr[-1]['instrAddress']) 
    schedule[-1]["BRANCH"] += 1 

    print("====Schedule=====")
    print(schedule)
    print("II value is:", II)

    return schedule

# Do the inequation to find about the correct II value

def can_schedule_instruction(schedule, dependencyTable, idx, instructions):
    """
    Computes the earliest cycle (bundle index) at which an instruction can be scheduled.
    
    Args:
        schedule (list): Current partial schedule.
        dependencyTable (dict).
        idx (int): Global index of the instruction to be scheduled.
        instructions (list).
    
    Returns:
        int: The minimum cycle delay (bundle index) at which the instruction can be legally scheduled.
    """
    dependency = dependencyTable[idx]
    min_delay = 0
    # Check each type of dependency
    for dep_type in ["localDependency", "loopInvarDep", "postLoopDep", "interloopDep"]:
        for dep in dependency[dep_type]:
            for i in range(len(schedule)):
                if dep[0] in schedule[i]["instructions"]:
                    delay = compute_delay(i, get_instruction_with_id(instructions, dep[0]))
                    min_delay = max(min_delay, delay)

    return min_delay


def bounded_ii(instructions):
    """
    Finds the minimal II allowing a valid ASAP schedule.
    
    Args:
        instructions (list): List of instruction objects.
        dependency_table (dict).
        initial_II (int).
        
    Returns:
        int: Minimal valid II.
    """
    op_counts = count_operations_per_class(instructions)
    ii_values = []

    for op_class, num_operations in op_counts.items():
        units = unit_limit[op_class]
        ii_values.append((num_operations / units))

    return max(ii_values)


def can_schedule_instruction_loop(schedule, dependencyTable, idx, instructions, II):
    """
    Computes the earliest cycle (bundle index) at which an instruction can be scheduled,
    while checking interloop dependency constraints with the current II.
    
    Args:
        schedule (list): Current partial schedule.
        dependencyTable (dict).
        idx (int): Global index of the instruction to be scheduled.
        instructions (list): Full list of parsed instructions.
        II (int): Minimal II.
    
    Returns:
        int: The minimum cycle delay (bundle index) at which the instruction can be legally scheduled,
             or -1 if interloop dependency constraint is violated (need to retry with higher II).
    """
    dependency = dependencyTable[idx]
    min_delay = 0

    # Check local, loop invariant, post-loop dependencies normally
    for dep_type in ["localDependency", "loopInvarDep", "postLoopDep"]:
        for dep in dependency[dep_type]:
            for i in range(len(schedule)):
                if dep[0] in schedule[i]["instructions"]:
                    delay = compute_delay(i, get_instruction_with_id(instructions, dep[0]))
                    min_delay = max(min_delay, delay)

    # Special check for interloop dependencies (critical for II constraint)
    for dep in dependency["interloopDep"]:
        for i in range(len(schedule)):
            if dep[0] in schedule[i]["instructions"]:
                producer_instr = get_instruction_with_id(instructions, dep[0])
                producer_cycle = i
                producer_latency = producer_instr["latency"]

                # Equation (2): must have S(P) + latency <= S(C) + II
                if producer_cycle + producer_latency > min_delay + II:
                    return -1  # Violation detected!

    return min_delay



def add_delay_BB0_dependency(scheduleBB0, scheduleBB1, dependencyTable, parsedInstruction):
    for idxBB1, instrBB1 in enumerate(scheduleBB1):
        for instBB1 in instrBB1["instructions"]:
            for dep_type in ["loopInvarDep", "interloopDep"]:
                for dep in get_instruction_with_id(dependencyTable,instBB1)[dep_type]:                  
                    # Check if the dependency is in BB0
                    for idxBB0, instrBB0 in enumerate(scheduleBB0):
                        for instBB0 in instrBB0["instructions"]:
                            if dep[0] == instBB0:#Here, we do dep[0] to take the instruction ID, dep return (id, register)
                                instructionBB0 = get_instruction_with_id(parsedInstruction,instBB0)
                                delay = compute_delay(0, instructionBB0)
                                while delay>compute_relative_distance(idxBB0, idxBB1, scheduleBB0):
                                    new_bundle = init_bundle()
                                    scheduleBB0.append(new_bundle)

def add_delay_BB2_dependency( scheduleBB1,scheduleBB2, dependencyTable, parsedInstruction):
    # Check if the dependency is in BB2
    for idxBB2, instrBB2 in enumerate(scheduleBB2):
        for instBB2 in instrBB2["instructions"]:
            for dep_type in ["postLoopDep"]:
                for dep in get_instruction_with_id(dependencyTable,instBB2)[dep_type]:   
                    #If there is, we check which instruction in BB1 is dependent on it
                                   
                    for idxBB1, instrBB1 in enumerate(scheduleBB1):
                        for instBB1 in instrBB1["instructions"]:
                            if dep[0] == instBB1:
                                instructionBB1 = get_instruction_with_id(parsedInstruction,instBB1)
                                delay = compute_delay(0, instructionBB1)
                                #Then we adjust the bubbles accrordingly
                                while delay>compute_relative_distance(idxBB1, idxBB2, scheduleBB1):
                                    new_bundle = init_bundle()
                                    scheduleBB2.insert(0,new_bundle)
                                    idxBB2 += 1
                                    
                                    
def compute_relative_distance(idxBB0, idxBB1, scheduleBB0):
    return (len(scheduleBB0) - idxBB0) + idxBB1