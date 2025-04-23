def simple_loop(dependencyTable, parsedInstruction, nbrAlu = 2, nbrMult = 1, nbrMem = 1, nbrBranch = 1,delay = 1, delayMult  =3):
    """
    This function simulates a simple loop scheduler. It takes in a dependency table and parsed instructions,
    and schedules the instructions based on their dependencies and available resources.
    """
    unit_limit = {
    "ALU": nbrAlu,
    "MULT": nbrMult,
    "MEM": nbrMem,
    "BRANCH": nbrBranch
}


    II = -1
    for instruction in parsedInstruction:
        if instruction["opcode"] == "loop":
            II = 0
            break
    if II == 0:
        schedule = []
        startIdx = -1
        for idx,instr in enumerate(parsedInstruction):
            if instr["opcode"] == "BB1":
                startIdx = idx+1
                break  # skip BBx markers
                
            unit = get_unit_type(instr)
            if unit == "WTF":
                print("Error: Unknown instruction type")
                continue
            # Try to place the instruction in the earliest possible bundle
            scheduled = False
            for bundle in schedule:
                if bundle[unit] < unit_limit[unit]:
                    bundle[unit] += 1
                    bundle["instrs"].append(instr["instrAddress"])
                    scheduled = True
                    break

            # If it couldn’t be placed, start a new bundle
            if not scheduled:
                new_bundle = init_bundle()
                new_bundle[unit] += 1
                new_bundle["instrs"].append(instr["instrAddress"])
                schedule.append(new_bundle)
        scheduleBB1  = []
        scheduleBB2  = []
        if startIdx != -1:
            
            for idx,instr in enumerate(parsedInstruction[startIdx:]):
                if instr["opcode"] == "BB2":
                    startIdx =startIdx+ idx+1
                    break  # skip BBx markers
                minDelay = can_schedule_instruction(scheduleBB1, dependencyTable, unit, instr, startIdx+idx, parsedInstruction)
                unit = get_unit_type(instr)
                if unit == "WTF":
                    print("Error: Unknown instruction type")
                    continue
                # Try to place the instruction in the earliest possible bundle
                scheduled = False
                for bundle in scheduleBB1:
                    if bundle[unit] < unit_limit[unit] :
                        
                        bundle[unit] += 1
                        bundle["instrs"].append(instr["instrAddress"])
                        scheduled = True
                        break

                # If it couldn’t be placed, start a new bundle
                if not scheduled:
                    new_bundle = init_bundle()
                    new_bundle[unit] += 1
                    new_bundle["instrs"].append(instr["instrAddress"])
                    scheduleBB1.append(new_bundle)
            
            for idx,instr in enumerate(parsedInstruction[startIdx:]):
                
                unit = get_unit_type(instr)
                if unit == "WTF":
                    print("Error: Unknown instruction type")
                    continue
                # Try to place the instruction in the earliest possible bundle
                scheduled = False
                for bundle in scheduleBB2:
                    if bundle[unit] < unit_limit[unit]:
                        bundle[unit] += 1
                        bundle["instrs"].append(instr["instrAddress"])
                        scheduled = True
                        break

                # If it couldn’t be placed, start a new bundle
                if not scheduled:
                    new_bundle = init_bundle()
                    new_bundle[unit] += 1
                    new_bundle["instrs"].append(instr["instrAddress"])
                    scheduleBB2.append(new_bundle)
                
        schedule = schedule + scheduleBB1 + scheduleBB2

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
                    delay = compute_delay(i, instructions[dep])  # pass instr directly
                    min_delay = max(min_delay, delay)
                print(f"Dependency {dep} found in cycle {i}, delay: {delay}")
                    

    print(f"Minimum delay for instruction {instr['instrAddress']} is {min_delay}")
    return min_delay

def compute_delay(scheduled_cycle, instr):
    """
    Returns the cycle when the result of an instruction is available.
    """
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
        
def get_unit_type(instr):
    if instr["opcode"] in ["add", "addi", "sub", "mov"]:
        return "ALU"
    elif instr["opcode"] == "mulu":
        return "MULT"
    elif instr["opcode"] in ["ld", "st"]:
        return "MEM"
    elif instr["opcode"].startswith("loop") or instr["opcode"].startswith("loop.pip"):
        return "BRANCH"
    return "WTF"


def init_bundle():
    return {
        "ALU": 0,
        "MULT": 0,
        "MEM": 0,
        "BRANCH": 0,
        "instrs": []
    }

