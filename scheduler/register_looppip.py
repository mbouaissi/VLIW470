from utils import *
import math
import re

def pip_register(schedule, loopSchedule, instructions, II, dependencyTable, non_modulo):

    print("===Starting renaming===")
    print("---Instructions---")
    print_schedule(instructions)
    print("---Dependencies---")
    print_schedule(dependencyTable)

    stride = II

    instructions = phase_one(loopSchedule, instructions, stride, dependencyTable)

    instructions = phase_two(loopSchedule, instructions, dependencyTable)

    instructions = phase_three(loopSchedule, instructions, dependencyTable, stride, non_modulo)

    instructions = phase_four(schedule, loopSchedule, instructions, dependencyTable, stride)

    return instructions

def phase_four(schedule, loopSchedule, instructions, dependencyTable, stride):

    print("====PHASE FOUR====")

    # Isolate BB0 instructions
    bb1_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB1"), len(instructions))
    bb2_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB2"), None)

    # Maps for easy access
    instr_map = {instr['instrAddress']: instr for instr in instructions[1:bb1_start]}
    dep_map = {entry['instrAddress']: entry for entry in dependencyTable}

    BB0_addrs = set(instr_map.keys())

    renamed_dest = set()

    for bundle in loopSchedule[:stride]:
        for instr_addr in bundle['instructions']:
            deps = dep_map.get(instr_addr, {})
            interloop_deps = deps.get('interloopDep', [])

            for producer_addr, reg in interloop_deps:
                if producer_addr in BB0_addrs and producer_addr not in renamed_dest:
                    producer_instr = instr_map[producer_addr]

                    dest = producer_instr['dest']
                    base, off = dest.split('(+')
                    iter_off, stage_off = [x.strip().lstrip('+').rstrip(')') for x in off.split(',')]

                    new_dest = f"{base}(+{int(iter_off)+1},+{stage_off})"
                    print(f"[Phase 4] Renaming BB0 Instr {producer_addr}: {dest} → {new_dest}")
                    producer_instr['dest'] = new_dest
                    renamed_dest.add(producer_addr)

    # Maps for easy access
    instr_map = {instr['instrAddress']: instr for instr in instructions[bb2_start+1:]}
    dep_map = {entry['instrAddress']: entry for entry in dependencyTable}

    for instr_addr in instr_map:
        deps = dep_map.get(instr_addr, {})
        post_loop_deps = deps.get('postLoopDep', [])
        cycle_c = len(loopSchedule) - 1  # assume consumer at last stage

        for producer_addr, reg in post_loop_deps:
            cycle_p = find_bundle_of_instr(producer_addr, loopSchedule)
            if cycle_p is None:
                print(f"[WARN] Producer {producer_addr} not found in loopSchedule.")
                continue

            stage_offset = math.floor((cycle_c - cycle_p) / stride)
            consumer_instr = instr_map[instr_addr]

            apply_postloop_stage_offset(consumer_instr, reg, stage_offset, instr_addr)

    print_schedule(instructions)

    return instructions

def apply_postloop_stage_offset(instr, reg, stage_inc, instr_addr):
    def patch_field(field):
        val = instr.get(field)
        if not val or not val.startswith(reg):
            return
        match = re.match(rf"{reg}\(\+(\d+),\+(\d+)\)", val)
        if not match:
            return
        iter_off = int(match.group(1))
        stage_off = int(match.group(2))
        new_val = f"{reg}(+{iter_off},+{stage_off + stage_inc})"
        print(f"[PostDep] Instr {instr_addr}: {field} = {val} → {new_val}")
        instr[field] = new_val

    def patch_mem_field(mem_field):
        val = instr.get(mem_field)
        if not val or f"({reg}(" not in val:
            return
        match = re.search(rf"{reg}\(\+(\d+),\+(\d+)\)", val)
        if not match:
            return
        iter_off = int(match.group(1))
        stage_off = int(match.group(2))
        new_reg = f"{reg}(+{iter_off},+{stage_off + stage_inc})"
        updated = re.sub(rf"{reg}\(\+\d+,\+\d+\)", new_reg, val)
        print(f"[PostDep] Instr {instr_addr}: {mem_field} = {val} → {updated}")
        instr[mem_field] = updated

    for field in ['src1', 'src2']:
        patch_field(field)

    if instr.get('opcode') == 'st':
        patch_field('dest')

    for mem_field in ['memSrc1', 'memSrc2']:
        patch_mem_field(mem_field)


def phase_three(loopSchedule, instructions, dependencyTable, stride, non_modulo):

    print("===Phase three===")

    # Map instruction address to bundle index
    instr_to_bundle = {
        instr_id: bundle_idx
        for bundle_idx, bundle in enumerate(non_modulo)
        for instr_id in bundle['instructions']
    }

    # Map instrAddress to actual instruction dict
    instr_map = {instr['instrAddress']: instr for instr in instructions}

    # Map dependencies
    dep_map = {entry['instrAddress']: entry for entry in dependencyTable}

    # === Initialization: Set all registers to xN(+0,+0) ===
    for instr in instructions:
        for field in ['dest', 'src1', 'src2']:
            val = instr.get(field)
            if val and val.startswith('x') and '(' not in val:
                instr[field] = f"{val}(+0,+0)"

        for mem_field in ['memSrc1', 'memSrc2']:
            val = instr.get(mem_field)
            if val and '(' in val:
                match = re.search(r'(x\d+)', val)
                if match:
                    reg = match.group(1)
                    instr[mem_field] = val.replace(f"({reg})", f"({reg}(+0,+0))")

    # === Dependency Handling ===
    for bundle in non_modulo:
        for instr_addr in bundle['instructions']:
            deps = dep_map.get(instr_addr, {})
            consumer_instr = instr_map.get(instr_addr)
            bundle_idx_consumer = instr_to_bundle[instr_addr]

            # ---- Local Dependencies (stage offset only) ----
            for producer_addr, _ in deps.get('localDependency', []):
                if producer_addr not in instr_to_bundle:
                    continue
                producer_instr = instr_map.get(producer_addr)
                bundle_idx_producer = instr_to_bundle[producer_addr]

                iter_increment = 0
                stage_increment = math.floor((bundle_idx_consumer - bundle_idx_producer) / stride)

                reg = producer_instr['dest']

                update_operand_offsets(consumer_instr, reg, iter_increment, stage_increment, instr_addr)

            # ---- Interloop Dependencies (stage offset + iteration offset = 1) ----
            for producer_addr, _ in deps.get('interloopDep', []):
                if producer_addr not in instr_to_bundle:
                    continue
                producer_instr = instr_map.get(producer_addr)
                bundle_idx_producer = instr_to_bundle[producer_addr]

                iter_increment = 1
                stage_increment = math.floor((bundle_idx_consumer - bundle_idx_producer) / stride)

                reg = producer_instr['dest']

                update_operand_offsets(consumer_instr, reg, iter_increment, stage_increment, instr_addr)

    print_schedule(instructions)

    return instructions


def update_operand_offsets(instr, reg, iter_inc, stage_inc, instr_addr):
    def update_field(field):
        val = instr.get(field)
        if not val or not reg in val:
            return

        # Extract register number (e.g., x41) and rebuild it
        match = re.match(r"x(\d+)", reg)
        if not match:
            return

        base = int(match.group(1))
        new_val = f"x{base}(+{iter_inc},+{stage_inc})"
        instr[field] = new_val
        print(f"[Phase 3] Instr {instr_addr}: field '{field}' changed from {val} to {new_val}")

    def update_mem_field(mem_field):
        val = instr.get(mem_field)
        if not val or f"({reg}" not in val:
            return

        match = re.search(rf"\((x\d+)(\([^)]+\))?\)", val)
        if match:
            base_reg = match.group(1)
            new_reg = f"{base_reg}(+{iter_inc},+{stage_inc})"
            updated_val = re.sub(rf"\({base_reg}(\([^)]+\))?\)", f"({new_reg})", val)
            instr[mem_field] = updated_val
            print(f"[Phase 3] Instr {instr_addr}: field '{mem_field}' changed from {val} to {updated_val}")

    for field in ['src1', 'src2']:
        update_field(field)

    if instr.get('opcode') == 'st':
        update_field('dest')

    for mem_field in ['memSrc1', 'memSrc2']:
        update_mem_field(mem_field)



def phase_two(loopSchedule, instructions, dependencyTable):

    print("===Phase two===")

    static_base = 1
    static_counter = 0

    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map = {entry['instrAddress']: entry for entry in dependencyTable}

    # To avoid renaming the same producer multiple times
    already_renamed = set()

    for bundle in loopSchedule:
        for instr_addr in bundle['instructions']:
            consumer_instr = instr_map.get(instr_addr)
            deps = dep_map.get(instr_addr, {})
            loop_invariant_deps = deps.get('loopInvarDep', [])

            updated_loop_invar_deps = []

            for producer_addr, producer_reg in loop_invariant_deps:
                producer_instr = instr_map.get(producer_addr)

                # Rename producer's dest only once
                if producer_addr not in already_renamed:
                    new_reg = f"x{static_base + static_counter}"
                    print(f"[Phase 2] Renaming producer @ addr {producer_addr}: {producer_instr['dest']} → {new_reg}")
                    producer_instr['dest'] = new_reg
                    static_counter += 1
                    already_renamed.add(producer_addr)
                    
                else:
                    new_reg = producer_instr['dest']

                # Update consumer fields if they match original reg
                for field in ['src1', 'src2', 'memSrc1', 'memSrc2']:
                    if consumer_instr.get(field) == producer_reg:
                        print(f"[Phase 2] Renaming consumer @ addr {instr_addr}: {consumer_instr[field]} → {new_reg}")
                        consumer_instr[field] = new_reg
                        

                # Update the dependencyTable entry
                updated_loop_invar_deps.append((producer_addr, new_reg))

            # Save updated deps back to dep_map
            dep_map[instr_addr]['loopInvarDep'] = updated_loop_invar_deps

    # Write back to original dependencyTable list
    dependencyTable[:] = list(dep_map.values())
    
    print_schedule(instructions)

    print("=Dependy Table=")
    print_schedule(dependencyTable)

    return instructions

def phase_one(loopSchedule, instructions, stride, dependencyTable):

    print("===Phase one===")

    rotating_base = 32
    rename_count = 0
    reg_rename_map = {}  # original dest → new rotating reg

    instr_map = {instr['instrAddress']: instr for instr in instructions}

    scheduled_instrs = [
        instr_id
        for bundle in loopSchedule[:stride]
        for instr_id in sorted(
            bundle['instructions'],
            key=lambda i: priority[get_unit_type(instr_map[i])]
        )
    ]

    # === Phase 1A: Assign new rotating registers to scheduled instructions ===
    for idx in scheduled_instrs:
        instr = instr_map[idx]

        if instr['opcode'] in ('st', 'loop') or instr['dest'] in ('LC', 'EC'):
            continue

        original_dest = instr['dest']
        new_reg = f'x{rotating_base + rename_count}'
        instr['dest'] = new_reg
        reg_rename_map[original_dest] = new_reg
        rename_count += stride

    # === Phase 1B: Propagate renaming to all operands in instructions ===
    for instr in instructions:
        # Update dest register if it's in the rename map
        if instr.get('dest') in reg_rename_map:
            instr['dest'] = reg_rename_map[instr['dest']]

        # Update source operands
        for field in ['src1', 'src2']:
            if instr.get(field) in reg_rename_map:
                instr[field] = reg_rename_map[instr[field]]

        # Update memory operands
        for mem_field in ['memSrc1', 'memSrc2']:
            mem_val = instr.get(mem_field)
            if not mem_val:
                continue
            for original, renamed in reg_rename_map.items():
                if f"({original})" in mem_val:
                    instr[mem_field] = mem_val.replace(f"({original})", f"({renamed})")

    # === Phase 1C: Update dependency table to reflect renamed registers ===
    reverse_rename_map = {v: k for k, v in reg_rename_map.items()}  # x34 → x2

    for entry in dependencyTable:
        for field in ['localDependency', 'interloopDep', 'loopInvarDep', 'postLoopDep']:
            if field not in entry:
                continue
            updated_deps = []
            for producer_addr, reg in entry[field]:
                producer_instr = instr_map.get(producer_addr)
                if not producer_instr:
                    updated_deps.append((producer_addr, reg))
                    continue

                renamed_dest = producer_instr.get('dest')
                # Look up the original name from the renamed one
                original_name = reverse_rename_map.get(renamed_dest, renamed_dest)

                # If the dep reg matches the original name, update to renamed
                if reg == original_name:
                    updated_deps.append((producer_addr, renamed_dest))
                else:
                    updated_deps.append((producer_addr, reg))

            entry[field] = updated_deps

    print_schedule(instructions)

    print("=Dependy Table=")
    print_schedule(dependencyTable)

    return instructions



