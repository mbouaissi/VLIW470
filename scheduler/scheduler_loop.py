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
                startIdx = idx
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
                    startIdx =startIdx+ idx
                    break  # skip BBx markers
                
                unit = get_unit_type(instr)
                if unit == "WTF":
                    print("Error: Unknown instruction type")
                    continue
                # Try to place the instruction in the earliest possible bundle
                scheduled = False
                for bundle in scheduleBB1:
                    if bundle[unit] < unit_limit[unit] :
                        can_schedule_instruction(scheduleBB1, dependencyTable, unit, instr)
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

def can_schedule_instruction(schedule, dependencyTable, unit, instr):
    """
    Checks if an instruction can be scheduled at the specified index in the schedule.
    """
    dependency = dependencyTable[instr["instrAddress"]]
    print(f"Checking dependencies for instruction {instr['instrAddress']}: {dependency}")

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

