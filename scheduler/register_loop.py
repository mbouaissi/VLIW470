from utils import *

def register_loop(schedule, parsedInstruction, dependencyTable):
    
    print("BEFORE MOVS")
    for i in parsedInstruction:
        print(i)
    schedule_with_reg = convert_back_to_register(schedule, parsedInstruction)
    schedule_sorted = sort_instructions_by_unit(schedule_with_reg)

    start_index = 1
    loop_dep = {}
    reg_transform = {}
    instr_to_bundle = []

    for i in dependencyTable:
        print(f"Interloop dep: {i['interloopDep']} for address {i['instrAddress']} and dest {get_instruction_with_id(parsedInstruction, i['instrAddress'])['dest']}")
# Flatten the bundles into a single list
    for bundle in schedule_sorted:
        instr_to_bundle.extend(bundle)

    # First pass: rename destination registers and record dependencies
    for idx, instr in enumerate(instr_to_bundle):
        if instr["opcode"] != "st" and instr["dest"] and instr["dest"].startswith("x"):
            new_reg = f"x{start_index}"
            loop_dep[new_reg] = None
            # Track dependency if dest == src1 or src2
            if instr["dest"] == instr["src1"]:
                loop_dep[new_reg] = instr["src1"]  # overwrite instead of appending
            if instr["dest"] == instr["src2"]:
                loop_dep[new_reg] = instr["src2"]  # overwrite instead of appending

            # Record the transformation
            reg_transform.setdefault(instr["dest"], []).append((new_reg, instr["instrAddress"]))
            instr["dest"] = new_reg

            print(f"Instruction: {idx}")
            print(f"\treg for {reg_transform}")

            start_index += 1

        print(f"Loop dep: {loop_dep}")

    
    # Second pass: update all sources to the newest available register
    for instr in instr_to_bundle:
        # Helper to update a single field
        def update_field(field_name):
            if instr[field_name] and instr[field_name].startswith("x"):
                old = instr[field_name]
                if old in reg_transform:
                    for new_reg, addr in reg_transform[old]:
                        if instr["instrAddress"] > addr:
                            instr[field_name] = new_reg
                            modify_dependency_table(dependencyTable, instr, new_reg, old, loop_dep)

        update_field("dest") if instr["opcode"] == "st" else None
        update_field("src1")
        update_field("src2")

        # Update memory sources
        def update_mem_src(mem_field, mem_field2):
            if instr[mem_field]:
                start = instr[mem_field].find('(')
                end = instr[mem_field].find(')')
                if start != -1 and end != -1:
                    reg_in_mem = instr[mem_field][start + 1:end]
                    if reg_in_mem in reg_transform:
                        for new_reg, addr in reg_transform[reg_in_mem]:
                            if instr["instrAddress"] > addr:
                                new_reg = instr[mem_field2]
                                instr[mem_field] = instr[mem_field].replace(reg_in_mem, new_reg)
                                print(f"Instruction: {instr['instrAddress']}")
                                print(f"\t{instr[mem_field]} -> {new_reg}")
                                modify_dependency_table(dependencyTable, instr, new_reg, reg_in_mem, loop_dep)
        update_mem_src("memSrc1", "src1")
        update_mem_src("memSrc2", "src2")
        
    loop_bundle_idx = next(
        (i for i, bundle in enumerate(schedule_sorted) for instr in bundle if instr["opcode"] == "loop"),
        None
    )
    
    interloop_movs = []

    for i, instr in reversed(list(enumerate(parsedInstruction))):
        if instr["opcode"].startswith("BB"):
            continue
        index_to_insert = instr["instrAddress"]
        break
    
    
    for renamed_reg, orig in loop_dep.items():
        if orig and orig != renamed_reg:
            index_to_insert += 1
            mov_instr = {
                "instrAddress": index_to_insert ,
                "opcode": "mov",
                "dest": orig,       
                "src1": renamed_reg, 
                "src2": None,
                "memSrc1": None,
                "memSrc2": None,
            }
            interloop_movs.append(mov_instr)

                
    parsedInstruction.extend(interloop_movs)
    print("AFTER MOVS")
    for i in parsedInstruction:
        print(i)
    for i in interloop_movs:
        delay = compute_min_delay_mov(parsedInstruction, schedule_sorted, i, loop_bundle_idx)
        if schedule[loop_bundle_idx]["ALU"]< unit_limit["ALU"] and delay == 0:
            schedule[loop_bundle_idx]["ALU"] += 1
            schedule[loop_bundle_idx]["instructions"].append(i["instrAddress"])
            
        else:
            loop_instrAddr = next((i["instrAddress"] for i in parsedInstruction if i["opcode"] == "loop"), None)
            
            schedule[loop_bundle_idx]["BRANCH"] = 0
            schedule[loop_bundle_idx]["instructions"].remove(loop_instrAddr) 
            if delay == 0:
                delay = 1
            for j in range(delay):
                new_bundle = init_bundle()
                schedule.insert(loop_bundle_idx +1, new_bundle)
                loop_bundle_idx += 1
            schedule[loop_bundle_idx]["ALU"] += 1
            schedule[loop_bundle_idx]["instructions"].append(i["instrAddress"])
            schedule[loop_bundle_idx]["BRANCH"] = 1
            schedule[loop_bundle_idx]["instructions"].append(loop_instrAddr)
            
                        
    return schedule, parsedInstruction

def modify_dependency_table(dependencyTable, instr, new_value, old_value, loop_dep ):
    """
    Modifies the dependency table to account for the new mov instructions.
    """
    for i in dependencyTable:
        for idx, j in enumerate(i["interloopDep"]):
            if j[0] == instr["instrAddress"] and j[1] == old_value:
                # Update the tuple in-place
                i["interloopDep"][idx] = (instr["instrAddress"], new_value)
                for k in loop_dep:
                    update_loop_dep_dict(loop_dep, old_value, new_value, k)

                

def compute_min_delay_mov(parsedInstruction, schedule, instruction, loop_index ):
    """
    Computes the minimum delay for the mov instructions.
    """
    register = instruction["src1"]
    delay = 0
    for idx, bundle in enumerate(schedule[:loop_index]):
        for instr in bundle:
            if instr["dest"] == register:
                
                delay = max((compute_delay(0,instr)+idx)-loop_index,delay)#Compute the delay with respect to the last bundle, so how many bundle we would need to add
    return delay
def insert_movs_before_loop(parsedInstruction, interloop_movs):
    # Find index of the first loop instruction 
    loop_index = next(
        i for i, instr in enumerate(parsedInstruction)
        if instr["opcode"] == "loop" and instr["instrAddress"] != -1
    )
    shift_amount = len(interloop_movs)
    # Shift only real instructions 
    for i in range(loop_index, len(parsedInstruction)):
        if parsedInstruction[i]["instrAddress"] != -1:
            parsedInstruction[i]["instrAddress"] += shift_amount

    # Assign instrAddress to interloop_movs 
    base_addr = parsedInstruction[loop_index]["instrAddress"] - shift_amount
    for offset, mov in enumerate(interloop_movs):
        mov["instrAddress"] = base_addr + offset

    #Find safe insertion point before loop and after last non-BB
    insert_index = loop_index
    while insert_index > 0 and parsedInstruction[insert_index - 1]["instrAddress"] == -1:
        insert_index -= 1

    parsedInstruction[insert_index:insert_index] = interloop_movs


def update_loop_dep_dict(loop_dep, old, new, key):
    value = loop_dep.get(key)
    if value == old:
        loop_dep[key] = new

def convert_back_to_register(schedule, parsedInstruction):
    """
    Converts the schedule back to register format.
    """
    new_schedule = []
    for cycle in schedule:
        bundle = []
        for instr in cycle["instructions"]:   
            instr_data = get_instruction_with_id(parsedInstruction, instr)
            if instr_data:
                bundle.append(instr_data)
        new_schedule.append(bundle)
    return new_schedule



# [' mov LC, 100', ' mov x1, 0x1000', ' nop', ' nop', ' nop']
# [' mov x2, 1', ' mov x3, 25', ' nop', ' nop', ' nop']
# [' addi x4, x1, 1', ' nop', ' nop', ' ld x5, 0(x1)', ' nop']
# [' nop', ' nop', ' mulu x6, x5, x3', ' nop', ' nop']
# [' nop', ' nop', ' mulu x7, x2, x5', ' nop', ' nop']
# [' nop', ' nop', ' nop', ' nop', ' nop']
# [' mov [[[0]]], x1', ' mov [[[0]]], x2', ' nop', ' st x6, 0(x1)', ' nop']
# [' mov [[[0]]], x3', " mov [[['x1']]], x4", ' nop', ' nop', ' nop']
# [' mov [[[0]]], x5', ' mov [[[0]]], x6', ' nop', ' nop', ' nop']
# [" mov [[['x3']]], x7", ' nop', ' nop', ' nop', ' loop 2']
# [' nop', ' nop', ' nop', ' st x7, 0(x4)', ' nop']
#  ~/epfl/comparch/VLIW470   main ±  
