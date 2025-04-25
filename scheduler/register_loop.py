from utils import get_instruction_with_id, get_unit_type, init_bundle, sort_instructions_by_unit, unit_limit


def register_loop(schedule,parsedInstruction, dependencyTable,):
    
    schedule = convert_back_to_register(schedule, parsedInstruction)
    schedule = sort_instructions_by_unit(schedule)
    
    
    start_index = 1
    loop_dep={}
    reg_transform = {}
    for idx, bundle in enumerate(schedule):
        for instr in bundle:
            if instr["opcode"] != "st" and instr["dest"] and instr["dest"].startswith("x"):
                new_reg = f"x{start_index}"
                loop_dep.setdefault(new_reg, [])
                if instr["dest"] == instr["src1"]:
                    loop_dep[new_reg].append(instr["src1"])
                if instr["dest"] == instr["src2"]:
                    loop_dep[new_reg].append(instr["src2"])
                if reg_transform.get(instr["dest"])is None:
                    reg_transform[instr["dest"]] = new_reg
                instr["dest"] = new_reg
                
                start_index += 1
    for k in schedule:  
        for l in k:
            dest = l["dest"]
            # src1
            if l["src1"] is not None and l["src1"].startswith("x"):
                old = l["src1"]
                new = reg_transform.get(old)
                if new and old != new:
                    l["src1"] = new
                    update_loop_dep_dict(loop_dep, old, new,dest)
                    # if loop_dep.get(new) is not None:
                    #     loop_dep[new] = []

            # src2
            if l["src2"] is not None and l["src2"].startswith("x"):
                old = l["src2"]
                new = reg_transform.get(old)
                if new and old != new:
                    l["src2"] = new
                    update_loop_dep_dict(loop_dep, old, new,dest)
                    # loop_dep.setdefault(new, []).append(old)

            # memSrc1
            if l["memSrc1"] is not None:
                start = l["memSrc1"].find('(')
                end = l["memSrc1"].find(')')
                if start != -1 and end != -1:
                    reg_in_mem = l["memSrc1"][start+1:end]
                    renamed = reg_transform.get(reg_in_mem)
                    if renamed and renamed != reg_in_mem:
                        l["memSrc1"] = l["memSrc1"].replace(reg_in_mem, renamed)
                        update_loop_dep_dict(loop_dep, reg_in_mem,renamed,dest)
                        # loop_dep.setdefault(renamed, []).append(reg_in_mem)

            # memSrc2
            if l["memSrc2"] is not None:
                start = l["memSrc2"].find('(')
                end = l["memSrc2"].find(')')
                if start != -1 and end != -1:
                    reg_in_mem = l["memSrc2"][start+1:end]
                    renamed = reg_transform.get(reg_in_mem)
                    if renamed and renamed != reg_in_mem:
                        l["memSrc2"] = l["memSrc2"].replace(reg_in_mem, renamed)
                        
                        update_loop_dep_dict(loop_dep, reg_in_mem,renamed,dest)    
                        # loop_dep.setdefault(renamed, []).append(reg_in_mem)
     
    loop_bundle_idx = next(
        (i for i, bundle in enumerate(schedule) for instr in bundle if instr["opcode"] == "loop"),
        None
    )
    
    for i in range(len(schedule)):
        schedule[i] = [instr for instr in schedule[i] if instr["instrAddress"] != -1]
    schedule = [bundle for bundle in schedule if len(bundle) > 0]   
    # Step: Insert movs before loop for loop-carried dependencies
    interloop_movs = []

    index_to_insert = 0#because of the bb in schedule lol
    for (renamed_reg, original_regs) in(loop_dep.items()):
        for orig in original_regs:
            if orig != renamed_reg:
                index_to_insert += 1
                mov_instr = {
                    "instrAddress": loop_bundle_idx + index_to_insert + 2,#+2 to take in account the BB
                    "opcode": "mov",
                    "dest": orig,       
                    "src1": renamed_reg, 
                    "src2": None,
                    "memSrc1": None,
                    "memSrc2": None,
                }
                interloop_movs.append(mov_instr)
    
    #parsedInstruction = [instr for instr in parsedInstruction if instr["instrAddress"] != -1]
    #parsedInstruction.sort(key=lambda instr: instr["instrAddress"])
    insert_movs_before_loop(parsedInstruction, interloop_movs)

                        
    return parsedInstruction
def insert_movs_before_loop(parsedInstruction, interloop_movs):
    # Step 1: Find index of the first 'loop' instruction (excluding BBs)
    loop_index = next(
        i for i, instr in enumerate(parsedInstruction)
        if instr["opcode"] == "loop" and instr["instrAddress"] != -1
    )

    shift_amount = len(interloop_movs)

    # Step 2: Shift only real instructions (ignore BBx with instrAddress == -1)
    for i in range(loop_index, len(parsedInstruction)):
        if parsedInstruction[i]["instrAddress"] != -1:
            parsedInstruction[i]["instrAddress"] += shift_amount

    # Step 3: Assign instrAddress to interloop_movs (based on loop's current addr - shift)
    base_addr = parsedInstruction[loop_index]["instrAddress"] - shift_amount
    for offset, mov in enumerate(interloop_movs):
        mov["instrAddress"] = base_addr + offset

    # Step 4: Find safe insertion point **before** loop and **after last non-BB**
    # We walk back from loop_index to find where to place the movs
    insert_index = loop_index
    while insert_index > 0 and parsedInstruction[insert_index - 1]["instrAddress"] == -1:
        insert_index -= 1

    # Step 5: Insert the mov instructions
    parsedInstruction[insert_index:insert_index] = interloop_movs


def update_loop_dep_dict(loop_dep, old, new, key):
    value = loop_dep.get(key)
    loop_dep[key] = [new if v == old else v for v in value]

def convert_back_to_register(schedule, parsedInstruction):
    """
    Converts the schedule back to register format.
    """
    new_schedule = []
    for cycle in schedule:
        bundle = []
        for instr in cycle["instrs"]:   
            instr_data = get_instruction_with_id(parsedInstruction, instr)
            if instr_data:
                bundle.append(instr_data)
        new_schedule.append(bundle)
    return new_schedule