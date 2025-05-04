from utils import *
import math
import re

def pip_register(schedule, loopSchedule, instructions, II, dependencyTable, non_modulo, modulo_schedule):

    normalize_memory_operands(instructions)

    phase_one(loopSchedule, instructions, II, modulo_schedule)

    phase_two(loopSchedule, instructions, dependencyTable)

    first_point_phase_four = phase_three(instructions, dependencyTable, II, non_modulo)

    phase_four(schedule, loopSchedule, instructions, dependencyTable, II, first_point_phase_four, non_modulo)


    return instructions

def phase_four(schedule, loopSchedule, instructions, dependencyTable, II, first_point_phase_four, non_modulo):
    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable}

    bb1_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB1"), len(instructions))
    bb2_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB2"), None)

    bb0_instructions = instructions[bb1_start+1:bb2_start]
    bb2_instructions = instructions[bb2_start+1:]

    changed_in_first_point = []

    instr_pos_in_sch = {
        instr_id: bundle_idx
        for bundle_idx, bundle in enumerate(schedule)
        for instr_id in bundle['instructions']
    }

    # === TREAT DEST OF BB0 ===
    # DOESN'T ACCOUNT FOR WHATEVER IS -St(P) (test really the stage distance) CAN ALREADY DO IT WITH NON MODULO (first iter) AND ADD THE PROLOGUE OVER
    for bundle in non_modulo:
        for instr_addr in bundle['instructions']:
            deps                 = dep_map.get(instr_addr, {})
            for producer_addr, _ in deps.get('interloopDep', []):
                producer_instr      = instr_map[producer_addr]
                if first_point_phase_four[instr_addr]['dep_reg'] == producer_instr['dest']:
                    new_reg = first_point_phase_four[instr_addr]['reg_to_update_w'] + 1
                    original_dest = producer_instr['dest']
                    producer_instr['dest'] = f'x{new_reg}'
                    print(f"[PHASE 4a: Rename dest from loop info] {original_dest} → {f'x{new_reg}'} @ instr {producer_addr}")
                    changed_in_first_point.append(producer_instr['instrAddress'])

    # === LOCAL DEP IN BB0 and BB2 ===
    # What does it mean same way as without loop.pip? Unless the destination register has already been allocated?
    for consumer_instr in bb0_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('localDependency', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']
            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    original_dest = consumer_instr[field]
                    consumer_instr[field] = producer_reg
                    print(f"[PHASE 4b: Rename consumer due to localDep BB0] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            original_dest = consumer_reg
                            consumer_instr[field] = producer_reg
                            print(f"[PHASE 4b: Rename consumer due to localDep BB0] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
    for consumer_instr in bb2_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('localDependency', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']
            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    original_dest = consumer_instr[field]
                    consumer_instr[field] = producer_reg
                    print(f"[PHASE 4b: Rename consumer due to localDep BB2] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            original_dest = consumer_reg
                            consumer_instr[field] = producer_reg
                            print(f"[PHASE 4b: Rename consumer due to localDep BB2] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    # === POST LOOP DEP (BB2) ===
    # Consumer assumed to be on last stage (test really the stage distance)
    # Use real schedule and last instruction with producer addr to compute stage distance
    # FIRST NEED TO CORRECT SCHEDULE
    for consumer_instr in bb2_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('postLoopDep', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']

            producer_stage = math.floor(instr_pos_in_sch[producer_addr]/II) # NEED TO GET MODULO SCHEDULE AND DO DIFFERENCE WITH NON MODULO TO GET LAST ITER OF EACH INSTR AND THEN CAN COMPUTE DISTANCE
            consumer_stage   = math.floor(instr_pos_in_sch[instr_addr]/II)

            increment = consumer_stage - producer_stage

            print(increment)

            reg_num = int(producer_reg.lstrip('x'))
            new_num = reg_num + increment

            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    original_dest = consumer_instr[field]
                    consumer_instr[field] = f"x{new_num}"
                    print(f"[PHASE 4c: Rename consumer due to postLoopDep] {original_dest} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            original_dest = consumer_reg
                            consumer_instr[field] = f"x{new_num}"
                            print(f"[PHASE 4c: Rename consumer due to postLoopDep] {original_dest} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
    return 




def phase_three(instructions, dependencyTable, II, non_modulo):
    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable}

    instr_pos_in_sch = {
        instr_id: bundle_idx
        for bundle_idx, bundle in enumerate(non_modulo)
        for instr_id in bundle['instructions']
    }

    first_point_phase_four = {}
    # === TREAT DEPENDENCIES ===
    for bundle in non_modulo:
        for instr_addr in bundle['instructions']:
            consumer_instr       = instr_map[instr_addr]
            deps                 = dep_map.get(instr_addr, {})

    # === TREAT LOOP INVARIANCE ===
            for producer_addr, dep_reg in deps.get('loopInvarDep'):
                producer_instr   = instr_map[producer_addr]
                producer_reg     = producer_instr['dest']
                if consumer_instr['opcode'] == 'st':
                    operands_type = ['dest']
                else:
                    operands_type = ['src1', 'src2']
                for field in operands_type:
                    if consumer_instr[field] == dep_reg:
                        original_dest = consumer_instr[field]
                        consumer_instr[field] = producer_reg
                        print(f"[PHASE 3: Rename consumer due to loopInvar] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                for field in ['memSrc1', 'memSrc2']:
                    val = consumer_instr.get(field)
                    if val and '(' in val:
                        match = re.search(r'(x\d+)', val)
                        if match:
                            consumer_reg = match.group(1)
                            if consumer_reg == dep_reg:
                                original_dest = consumer_reg
                                consumer_instr[field] = producer_reg
                                print(f"[PHASE 3: Rename consumer due to loopInvar] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                       
    # === TREAT LOCAL DEPENDENCIES ===
            for producer_addr, dep_reg in deps.get('localDependency', []):
                producer_instr      = instr_map[producer_addr]

                producer_stage = math.floor(instr_pos_in_sch[producer_addr]/II)
                consumer_stage   = math.floor(instr_pos_in_sch[instr_addr]/II)

                increment = consumer_stage - producer_stage 

                if consumer_instr['opcode'] == 'st':
                    operands_type = ['dest']
                else:
                    operands_type = ['src1', 'src2']
                for field in operands_type:
                    if consumer_instr[field] == dep_reg:
                        producer_reg = producer_instr['dest']
                        reg_num = int(producer_reg.lstrip('x'))
                        new_num = reg_num + increment
                        consumer_instr[field] = f"x{new_num}"
                        print(f"[PHASE 3: Rename consumer due to localDep] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                for field in ['memSrc1', 'memSrc2']:
                    val = consumer_instr.get(field)
                    if val and '(' in val:
                        match = re.search(r'(x\d+)', val)
                        if match:
                            consumer_reg = match.group(1)
                            if consumer_reg == dep_reg:
                                producer_reg = producer_instr['dest']
                                reg_num = int(producer_reg.lstrip('x'))
                                new_num = reg_num + increment
                                consumer_instr[field] = f"x{new_num}"
                                print(f"[PHASE 3: Rename consumer due to localDep] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    # === TREAT INTERLOOP ===
    
            for producer_addr, dep_reg in deps.get('interloopDep', []):
                producer_instr      = instr_map[producer_addr]

                if producer_addr not in instr_pos_in_sch.keys():
                    continue

                producer_stage = math.floor(instr_pos_in_sch[producer_addr]/II)
                consumer_stage   = math.floor(instr_pos_in_sch[instr_addr]/II)

                increment = consumer_stage - producer_stage + 1

                if consumer_instr['opcode'] == 'st':
                    operands_type = ['dest']
                else:
                    operands_type = ['src1', 'src2']
                for field in operands_type:
                    if consumer_instr[field] == dep_reg:
                        producer_reg = producer_instr['dest']
                        reg_num = int(producer_reg.lstrip('x'))
                        new_num = reg_num + increment
                        first_point_phase_four[instr_addr] = reg_num

                        first_point_phase_four[instr_addr] = {
                            'reg_to_update_w':  reg_num,
                            'dep_reg':        dep_reg
                        }
                        consumer_instr[field] = f"x{new_num}"
                        print(f"[PHASE 3: Rename consumer due to Interloop] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                for field in ['memSrc1', 'memSrc2']:
                    val = consumer_instr.get(field)
                    if val and '(' in val:
                        match = re.search(r'(x\d+)', val)
                        if match:
                            consumer_reg = match.group(1)
                            if consumer_reg == dep_reg:
                                producer_reg = producer_instr['dest']
                                reg_num = int(producer_reg.lstrip('x'))
                                first_point_phase_four[instr_addr] = {
                                    'reg_to_update_w':  reg_num,
                                    'dep_reg':        dep_reg
                                }
                                new_num = reg_num + increment
                                consumer_instr[field] = f"x{new_num}"
                                print(f"[PHASE 3: Rename consumer due to Interloop] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    return first_point_phase_four


def phase_two(loopSchedule, instructions, dependencyTable):
    static_reg = 1

    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable}

    already_renamed = set()


    # === FIND LOOP INVARIANCES ===
    for bundle in loopSchedule:
        for instr_addr in bundle['instructions']:
            deps           = dep_map.get(instr_addr, {})
            loop_invar_deps = deps.get('loopInvarDep', [])

            # === RENAME LOOP INVARIANCE PRODUCER ===
            for producer_addr, producer_reg in loop_invar_deps:
                producer_instr = instr_map.get(producer_addr)
                if producer_addr not in already_renamed:
                    original_dest = producer_instr['dest']
                    new_reg = f"x{static_reg}"
                    producer_instr['dest'] = new_reg
                    print(f"[PHASE 2: Rename producer] {original_dest} → {new_reg} @ instr {producer_addr}")
                    static_reg += 1
                    already_renamed.add(producer_addr)
                else:
                    # If has already been renamed get his renamed value
                    new_reg = producer_instr['dest']

    return


def phase_one(loopSchedule, instructions, II, modulo_schedule):
    step = count_stages(modulo_schedule) + 1
    rotating_base = 32
    rename_count       = 0

    instr_map = {instr['instrAddress']: instr for instr in instructions}


    # === SELECT INSTRUCTIONS TO ROTATE ===
    scheduled_instrs = [
        instr_id
        for bundle in loopSchedule[:II]
        for instr_id in sorted(
            bundle['instructions'],
            key=lambda i: priority[get_unit_type(instr_map[i])]
        )
    ]
    # === ASSIGN ROTATING REGISTERS ===
    for addr in scheduled_instrs:
        instr = instr_map[addr]
        if instr['opcode'] in ('st', 'loop') or instr['dest'] in ('LC', 'EC'):
            continue

        original_dest = instr['dest']
        new_reg = f'x{rotating_base + rename_count}'
        instr['dest'] = new_reg

        print(f"[PHASE 1: Rename dest] {original_dest} → {new_reg} @ instr {addr}")
        rename_count += step

    return 
