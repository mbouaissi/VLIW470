from utils import *


def register_loop(schedule, parsedInstructions, dependencyTable):
    schedule_with_instructions = reconstruct_instruction_schedule(schedule, parsedInstructions)
    schedule_sorted = sort_instructions_by_unit(schedule_with_instructions)

    reg_rename_counter = 1
    interloop_dependency_map = {}
    register_renaming_map = {}
    flattened_schedule = []

    # Debug: show current interloop dependencies
    for entry in dependencyTable:
        print(f"Interloop dependency: {entry['interloopDep']} for address {entry['instrAddress']} and destination {get_instruction_with_id(parsedInstructions, entry['instrAddress'])['dest']}")

    # Flatten instruction bundles into a single list
    for instruction_bundle in schedule_sorted:
        flattened_schedule.extend(instruction_bundle)

    # First pass: Rename destination registers and record initial dependencies
    for idx, instruction in enumerate(flattened_schedule):
        if instruction["opcode"] != "st" and instruction["dest"] and instruction["dest"].startswith("x"):
            new_register = f"x{reg_rename_counter}"
            interloop_dependency_map[new_register] = None

            if instruction["dest"] == instruction["src1"]:
                interloop_dependency_map[new_register] = instruction["src1"]
            if instruction["dest"] == instruction["src2"]:
                interloop_dependency_map[new_register] = instruction["src2"]

            register_renaming_map.setdefault(instruction["dest"], []).append((new_register, instruction["instrAddress"]))
            instruction["dest"] = new_register

            print(f"Instruction {idx}: register renaming map updated: {register_renaming_map}")
            reg_rename_counter += 1

        print(f"Interloop dependency map: {interloop_dependency_map}")

    # Second pass: Update sources to match new register names
    def update_memory_source(mem_field, mem_src_field):
        if instruction[mem_field]:
            start = instruction[mem_field].find('(')
            end = instruction[mem_field].find(')')
            if start != -1 and end != -1:
                reg_in_mem = instruction[mem_field][start + 1:end]
                if reg_in_mem in register_renaming_map:
                    for new_reg, addr in register_renaming_map[reg_in_mem]:
                        if instruction["instrAddress"] > addr :
                            
                            print(f"Updating memory source§ {addr} from {instruction['instrAddress']} to {new_reg}")

                            new_reg_to_use = instruction[mem_src_field]
                            instruction[mem_field] = instruction[mem_field].replace(reg_in_mem, new_reg_to_use)
                            for tuple in get_instruction_with_id(dependencyTable,instruction["instrAddress"])["interloopDep"]:
                                
                                if  addr == tuple[0]:
                                    update_interloop_dependency_table(dependencyTable, instruction, new_reg_to_use, reg_in_mem, interloop_dependency_map)

    def update_field(field_name):
        if instruction[field_name] and instruction[field_name].startswith("x"):
            old_reg = instruction[field_name]
            if old_reg in register_renaming_map:
                for new_reg, addr in register_renaming_map[old_reg]:
                    if instruction["instrAddress"] > addr :
                        print(f"Updating memory source {addr} from {instruction['instrAddress']} to {new_reg}")
                        instruction[field_name] = new_reg                            
                        for tuple in get_instruction_with_id(dependencyTable,instruction["instrAddress"])["interloopDep"]:
                            print(f"Address {addr} from tuple {tuple} and {addr==tuple[0]}")        
                            if  addr == tuple[0]:
                                update_interloop_dependency_table(dependencyTable, instruction, new_reg, old_reg, interloop_dependency_map)

    for instruction in flattened_schedule:
        print("==========================")
        print(f"BEFORE instruction {instruction['instrAddress']}, {instruction}:")
        print("\t", interloop_dependency_map)

        if instruction["opcode"] == "st":
            update_field("dest")
        update_field("src1")
        update_field("src2")
        update_memory_source("memSrc1", "src1")
        update_memory_source("memSrc2", "src2")

        print("AFTER:")
        print("\t", interloop_dependency_map)

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
        if original and original != renamed_register:
            print(f"Adding mov from {renamed_register} to {original}")
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
        print(f"Loop bundle index: {loop_instruction}")
    
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
                print(f"Dependency found for {mov_instruction['instrAddress']} with {instr['instrAddress']}")
                print(f"Delay: {(compute_delay(0, instr) + idx)}")
                delay = max((compute_delay(0, instr) + idx) - loop_index, delay)
    return delay

def update_interloop_dependency_table(dependencyTable, instruction, new_value, old_value, interloop_dependency_map):
    for entry in dependencyTable:
        for idx, (instrAddr, reg) in enumerate(entry["interloopDep"]):
            if instrAddr == instruction["instrAddress"]:
                print(f"Updating dependency table for {instruction['instrAddress']} from {old_value} to {new_value}")
                entry["interloopDep"][idx] = (instruction["instrAddress"], new_value)
                for key in interloop_dependency_map:
                    propagate_register_update_in_dependency_map(interloop_dependency_map, old_value, new_value, key)

def propagate_register_update_in_dependency_map(interloop_dependency_map, old_register, new_register, key):
    if interloop_dependency_map.get(key) == old_register:
        interloop_dependency_map[key] = new_register
