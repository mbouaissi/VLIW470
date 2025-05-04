from utils import *


def register_loop(schedule, parsedInstructions, dependencyTable):
    schedule_with_instructions = reconstruct_instruction_schedule(schedule, parsedInstructions)
    schedule_sorted = sort_instructions_by_unit(schedule_with_instructions)

    reg_rename_counter = 1
    interloop_dependency_map = {}
    register_renaming_map = {}
    flattened_schedule = []

    # Flatten instruction bundles into a single list
    for instruction_bundle in schedule_sorted:
        flattened_schedule.extend(instruction_bundle)

    # First pass: Rename destination registers and record initial dependencies
    no_more_interloop_possible = False
    for idx, instruction in enumerate(flattened_schedule):
        if instruction["opcode"] == "loop":
            no_more_interloop_possible = True
            continue
        if instruction["opcode"] != "st" and instruction["dest"] and instruction["dest"].startswith("x"):
            new_register = f"x{reg_rename_counter}"
            interloop_dependency_map[new_register] = None
            
            if instruction["dest"] == instruction["src1"] and not no_more_interloop_possible and is_reg_in_dependency_table(dependencyTable, "interloopDep", instruction["src1"]):
                interloop_dependency_map[new_register] = instruction["src1"]
            if instruction["dest"] == instruction["src2"]and not no_more_interloop_possible and is_reg_in_dependency_table(dependencyTable, "interloopDep", instruction["src1"]):
                interloop_dependency_map[new_register] = instruction["src2"]
            
            register_renaming_map.setdefault(instruction["dest"], []).append((new_register, instruction["instrAddress"]))
            instruction["dest"] = new_register
            reg_rename_counter += 1
    
    for idx, instruction in enumerate(flattened_schedule):
       # print(f"Instruction {idx}: {instruction}")
        if instruction["opcode"] == "st":
            reg_in_mem = instruction["dest"]
            if reg_in_mem is not None:
                if reg_in_mem not in register_renaming_map and reg_in_mem.startswith("x"):
                    new_reg_to_use = f"x{reg_rename_counter}"
                  #  print(f"Renaming222 {reg_in_mem} to {new_reg_to_use}")
                    #register_renaming_map.setdefault(instruction["dest"], []).append((new_reg_to_use, instruction["instrAddress"]))
                    instruction["dest"] = new_reg_to_use
                    reg_rename_counter += 1
        if instruction["opcode"] == "ld" or instruction["opcode"] == "st":
            start = instruction["memSrc1"].find('(')
            end = instruction["memSrc1"].find(')')
            start = instruction["memSrc1"].find('(')
            end = instruction["memSrc1"].find(')')
            if start != -1 and end != -1:
                reg_in_mem = instruction["memSrc1"][start + 1:end]
                if reg_in_mem not in register_renaming_map:
                    # print  (f"Register {reg_in_mem} not in renaming map")
                    new_reg_to_use = f"x{reg_rename_counter}"
                    # Safely replace only inside the (reg) part of offset(reg)
                    start = instruction["memSrc1"].find('(')
                    end = instruction["memSrc1"].find(')')
                    if start != -1 and end != -1:
                        #register_renaming_map.setdefault(instruction["memSrc1"], []).append((new_reg_to_use, instruction["instrAddress"]))
                        instruction["memSrc1"] = instruction["memSrc1"][:start + 1] + new_reg_to_use + instruction["memSrc1"][end:]
                        reg_rename_counter += 1
        else:
            reg_in_mem = instruction["src1"]
            if reg_in_mem is not None:
                if reg_in_mem not in register_renaming_map and reg_in_mem.startswith("x"):
                    new_reg_to_use = f"x{reg_rename_counter}"
                  #  print(f"Renaming222 {reg_in_mem} to {new_reg_to_use}")
                    #register_renaming_map.setdefault(instruction["src1"], []).append((new_reg_to_use, instruction["instrAddress"]))
                    instruction["src1"] = new_reg_to_use
                    reg_rename_counter += 1
            reg_in_mem = instruction["src2"]
            if reg_in_mem is not None:
                if reg_in_mem not in register_renaming_map and reg_in_mem.startswith("x"):
                    
                    new_reg_to_use = f"x{reg_rename_counter}"
                   # print(f"Renaming222 {reg_in_mem} to {new_reg_to_use}")

                    instruction["src2"] = new_reg_to_use
                    reg_rename_counter += 1
    # Second pass: Update sources to match new register names
    def update_memory_source(mem_field, mem_src_field, dep):
        if instruction[mem_field]:
            start = instruction[mem_field].find('(')
            end = instruction[mem_field].find(')')
            if start != -1 and end != -1:
                reg_in_mem = instruction[mem_field][start + 1:end]
                
                if dep==reg_in_mem and reg_in_mem in register_renaming_map:
                    for new_reg, addr in register_renaming_map[reg_in_mem]:
                        if instruction["instrAddress"] > addr :
                            new_reg_to_use = instruction[mem_src_field]
                            # Safely replace only inside the (reg) part of offset(reg)
                            start = instruction[mem_field].find('(')
                            end = instruction[mem_field].find(')')
                            if start != -1 and end != -1:
                                old = instruction[mem_field][start + 1:end]
                                instruction[mem_field] = instruction[mem_field][:start + 1] + new_reg_to_use + instruction[mem_field][end:]
                            for tuple in get_instruction_with_id(dependencyTable,instruction["instrAddress"])["interloopDep"]:
                                if  addr == tuple[0]:
                                    update_interloop_dependency_table(dependencyTable, instruction, new_reg_to_use, reg_in_mem, interloop_dependency_map)

    def update_field(field_name, dep):
        if instruction[field_name] and instruction[field_name].startswith("x"):
            old_reg = instruction[field_name]
        
            if dep == old_reg and old_reg in register_renaming_map:
                for new_reg, addr in register_renaming_map[old_reg]:
                    if instruction["instrAddress"] > addr :
                        instruction[field_name] = new_reg        
                        for tuple in get_instruction_with_id(dependencyTable,instruction["instrAddress"])["interloopDep"]:
                            if  addr == tuple[0]:
                                update_interloop_dependency_table(dependencyTable, instruction, new_reg, old_reg, interloop_dependency_map)

    for instruction in flattened_schedule:
        for dep_type in ["interloopDep", "localDependency", "loopInvarDep","postLoopDep"]:
            for entry in get_instruction_with_id(dependencyTable, instruction["instrAddress"])[dep_type]:            
                entry[1]
                if instruction["opcode"] == "st":
                    update_field("dest", entry[1])
                update_field("src1", entry[1])
                update_field("src2", entry[1])
                update_memory_source("memSrc1", "src1", entry[1])
                update_memory_source("memSrc2", "src2", entry[1])
    # Find loop bundle index
    loop_bundle_index = next(
        (i for i, bundle in enumerate(schedule_sorted) for instr in bundle if instr["opcode"] == "loop"),
        None
    )

    interloop_mov_instructions = []

    # Find address where to start inserting new movs
    for i, instruction in reversed(list(enumerate(parsedInstructions))):
        if instruction["opcode"].startswith("BB"):
            continue
        insert_address = instruction["instrAddress"]
        break
    
    for renamed_register, original in interloop_dependency_map.items():        
        # Check if renamed_register actually has a dependency
        has_dependency = True
        if original and original != renamed_register and has_dependency:
            insert_address += 1
            mov_instruction = {
                "instrAddress": insert_address,
                "opcode": "mov",
                "dest": original,
                "src1": renamed_register,
                "src2": None,
                "memSrc1": None,
                "memSrc2": None,
            }
            interloop_mov_instructions.append(mov_instruction)

    parsedInstructions.extend(interloop_mov_instructions)

    # Schedule the mov instructions
    
    for mov in interloop_mov_instructions:
        delay = calculate_mov_insertion_delay(parsedInstructions, schedule_sorted, mov, loop_bundle_index)
        if schedule[loop_bundle_index]["ALU"] < unit_limit["ALU"] and delay == 0:
            schedule[loop_bundle_index]["ALU"] += 1
            schedule[loop_bundle_index]["instructions"].append(mov["instrAddress"])
        else:
            loop_instr_address = next((instr["instrAddress"] for instr in parsedInstructions if instr["opcode"] == "loop"), None)
            schedule[loop_bundle_index]["BRANCH"] = 0
            schedule[loop_bundle_index]["instructions"].remove(loop_instr_address)

            if delay == 0:
                delay = 1

            for _ in range(delay):
                new_bundle = init_bundle()
                schedule.insert(loop_bundle_index + 1, new_bundle)
                loop_bundle_index += 1

            schedule[loop_bundle_index]["ALU"] += 1
            schedule[loop_bundle_index]["instructions"].append(mov["instrAddress"])
            schedule[loop_bundle_index]["BRANCH"] = 1
            schedule[loop_bundle_index]["instructions"].append(loop_instr_address)
    if loop_bundle_index is not None:
        for i in schedule[loop_bundle_index]["instructions"]:
            loop_instruction = get_instruction_with_id(parsedInstructions, i)
            hasChanged = False
            if loop_instruction and loop_instruction["opcode"] == "loop":
                for position, bundle in enumerate(schedule):
                    for instr_idx in bundle["instructions"]:
                        instruction = get_instruction_with_id(parsedInstructions, instr_idx)
                        if str(instruction["instrAddress"]) == str(loop_instruction["dest"]):
                            loop_instruction["dest"] = position
                            hasChanged = True
                            break
                    if hasChanged:
                        break
    
    return schedule, parsedInstructions


def reconstruct_instruction_schedule(schedule, parsedInstructions):
    new_schedule = []
    for cycle in schedule:
        bundle = []
        for instr_addr in cycle["instructions"]:
            instr_data = get_instruction_with_id(parsedInstructions, instr_addr)
            if instr_data:
                bundle.append(instr_data)
        new_schedule.append(bundle)
    return new_schedule



def calculate_mov_insertion_delay(parsedInstructions, schedule, mov_instruction, loop_index):
    register = mov_instruction["src1"]
    delay = 0
    for idx, bundle in enumerate(schedule[:loop_index+1]):
        for instr in bundle:
            if instr["dest"] == register:
                delay = max((compute_delay(0, instr) + idx) - loop_index, delay)
    return delay

def update_interloop_dependency_table(dependencyTable, instruction, new_value, old_value, interloop_dependency_map):
    for entry in dependencyTable:
        for idx, (instrAddr, reg) in enumerate(entry["interloopDep"]):
            if instrAddr == instruction["instrAddress"]:
                entry["interloopDep"][idx] = (instruction["instrAddress"], new_value)
                for key in interloop_dependency_map:
                    propagate_register_update_in_dependency_map(interloop_dependency_map, old_value, new_value, key)

def propagate_register_update_in_dependency_map(interloop_dependency_map, old_register, new_register, key):
    if interloop_dependency_map.get(key) == old_register:
        interloop_dependency_map[key] = new_register

def is_reg_in_dependency_table(dependencyTable, field, reg):
    for entry in dependencyTable:
        for j in entry[field]:
            # print(j, reg, str(j[1]) == str(reg)) 
            if str(j[1]) == str(reg):
                return True
    return False
