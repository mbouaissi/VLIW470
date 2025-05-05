from utils import *
import math
import re

def pip_register(schedule, instructions, II, dependencyTable, non_modulo, modulo_schedule, parsedInstruction):

    #print("===schedule===")
    print_schedule(schedule)
    #print("===non_modulo===")
    print_schedule(non_modulo)
    #print("===modulo_schedule===")
    print_schedule(modulo_schedule)

    normalize_memory_operands(instructions)

    has_been_allocated_phase1 = phase_one(instructions, II, modulo_schedule)

    phase_two(modulo_schedule, instructions, dependencyTable)

    first_point_phase_four = phase_three(instructions, dependencyTable, II, non_modulo)

    phase_four(schedule, modulo_schedule, instructions, dependencyTable, II, first_point_phase_four, non_modulo, parsedInstruction, has_been_allocated_phase1)


    return instructions

def phase_four(schedule, modulo_schedule, instructions, dependencyTable, II, first_point_phase_four, non_modulo, parsedInstruction, has_been_allocated_phase1):
    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable}

    bb1_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB1"), len(instructions))
    bb2_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB2"), None)

    bb0_instructions = instructions[:bb1_start+1]
    bb1_instructions = instructions[bb1_start+1:bb2_start]
    bb2_instructions = instructions[bb2_start+1:]

    changed_in_first_point = []

    instr_pos_in_non_modulo = {
        instr_id: bundle_idx
        for bundle_idx, bundle in enumerate(non_modulo)
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
                    #print(f"[PHASE 4a: Rename dest from loop info] {original_dest} → {f'x{new_reg}'} @ instr {producer_addr}")
                    changed_in_first_point.append(producer_instr['instrAddress'])

    # === LOCAL DEP IN BB0 and BB2 ===
    # What does it mean same way as without loop.pip? Unless the destination register has already been allocated?


    free_regs = get_free_static(instructions)
    #print("=== FREE REGS===")
    #print(free_regs)

    for consumer_instr in bb0_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('localDependency', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']
            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest', 'src1']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    if (producer_addr in has_been_allocated_phase1):
                        original_dest = consumer_instr[field]
                        consumer_instr[field] = producer_instr['dest']
                        ##print(f"[PHASE 4b: Rename consumer due to localDep BB0] {original_dest} → {producer_instr['dest']} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                    else:
                        original_dest = consumer_instr[field]
                        original_dest_prod = producer_instr['dest']
                        producer_instr['dest'] = free_regs[0]
                        free_regs.pop(0)
                        consumer_instr[field] = producer_instr['dest']
                        has_been_allocated_phase1[producer_addr] = producer_instr[field]
                        ##print("=== FREE REGS===")
                        ##print(free_regs)
                        ##print(f"[PHASE 4b: Rename consumer due to localDep BB0 like loop] {original_dest} → {producer_instr['dest']} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                        ##print(f"[PHASE 4b: Rename producer due to localDep BB0 like loop] {original_dest_prod} → {producer_instr['dest']} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            offset, _, _ = val.partition('(') 
                            original_dest = consumer_reg
                            consumer_instr[field] = f"{offset}({producer_reg})"
                            #print(f"[PHASE 4b: Rename consumer due to localDep BB0] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
        for consumer_instr in bb1_instructions:
            instr_addr = consumer_instr['instrAddress']
            deps       = dep_map.get(instr_addr, {})
            for producer_addr, dep_reg in deps.get('localDependency', []):
                producer_instr      = instr_map[producer_addr]
                producer_reg        = producer_instr['dest']
                if consumer_instr['opcode'] == 'st':
                    operands_type = ['dest', 'src1']
                else:
                    operands_type = ['src1', 'src2']
                for field in operands_type:
                    if consumer_instr[field] == dep_reg:
                        if (producer_addr in has_been_allocated_phase1):
                            original_dest = consumer_instr[field]
                            consumer_instr[field] = producer_instr['dest']
                            #print(f"[PHASE 4b: Rename consumer due to localDep BB2] {original_dest} → {producer_instr['dest']} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                            print_schedule(instructions)
                        else:
                            original_dest = consumer_instr[field]
                            original_dest_prod = producer_instr['dest']
                            producer_instr['dest'] = free_regs[0]
                            free_regs.pop(0)
                            consumer_instr[field] = producer_instr['dest']
                            has_been_allocated_phase1[producer_addr] = producer_instr[field]
                            #print(f"[PHASE 4b: Rename consumer due to localDep BB2 like loop] {original_dest} → {producer_instr['dest']} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                            #print(f"[PHASE 4b: Rename producer due to localDep BB2 like loop] {original_dest_prod} → {producer_instr['dest']} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                            print_schedule(instructions)
                for field in ['memSrc1', 'memSrc2']:
                    val = consumer_instr.get(field)
                    if val and '(' in val:
                        match = re.search(r'(x\d+)', val)
                        if match:
                            consumer_reg = match.group(1)
                            if consumer_reg == dep_reg:
                                offset, _, _ = val.partition('(') 
                                original_dest = consumer_reg
                                consumer_instr[field] = f"{offset}({producer_reg})"
                                #print(f"[PHASE 4b: Rename consumer due to localDep BB0] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    # === POST LOOP DEP (BB2) ===
    for consumer_instr in bb2_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('postLoopDep', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']

            last_branch_idx = max(i for i, b in enumerate(non_modulo) if b['BRANCH'] > 0)
            producer_stage = math.floor(instr_pos_in_non_modulo[producer_addr]/II)
            consumer_stage   = math.floor(last_branch_idx/II)
            increment = consumer_stage - producer_stage
            reg_num = int(producer_reg.lstrip('x'))
            new_num = reg_num + increment

            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest', 'src1']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    original_dest = consumer_instr[field]
                    consumer_instr[field] = f"x{new_num}"
                    #print(f"[PHASE 4c: Rename consumer due to postLoopDep] {original_dest} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            original_dest = consumer_reg
                            offset, _, _ = val.partition('(')  
                            consumer_instr[field] = f"{offset}(x{new_num})"
                            #print(f"[PHASE 4c: Rename consumer due to postLoopDep] {original_dest} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    # === LOOP INVARIANT IN BB0 and BB2 ===
    for consumer_instr in bb0_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('loopInvarDep', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']
            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest', 'src1']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    original_dest = consumer_instr[field]
                    consumer_instr[field] = producer_reg
                    #print(f"[PHASE 4d: Rename consumer due to loopInvarDep BB0] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            offset, _, _ = val.partition('(') 
                            original_dest = consumer_reg
                            consumer_instr[field] = f"{offset}({producer_reg})"
                            #print(f"[PHASE 4d: Rename consumer due to loopInvarDep BB0] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
    for consumer_instr in bb2_instructions:
        instr_addr = consumer_instr['instrAddress']
        deps       = dep_map.get(instr_addr, {})
        for producer_addr, dep_reg in deps.get('loopInvarDep', []):
            producer_instr      = instr_map[producer_addr]
            producer_reg        = producer_instr['dest']
            if consumer_instr['opcode'] == 'st':
                operands_type = ['dest', 'src1']
            else:
                operands_type = ['src1', 'src2']
            for field in operands_type:
                if consumer_instr[field] == dep_reg:
                    original_dest = consumer_instr[field]
                    consumer_instr[field] = producer_reg
                    #print(f"[PHASE 4d: Rename consumer due to loopInvarDep BB2] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
            for field in ['memSrc1', 'memSrc2']:
                val = consumer_instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        consumer_reg = match.group(1)
                        if consumer_reg == dep_reg:
                            offset, _, _ = val.partition('(') 
                            original_dest = consumer_reg
                            consumer_instr[field] = f"{offset}({producer_reg})"
                            #print(f"[PHASE 4d: Rename consumer due to loopInvarDep BB2] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    # === TREAT NEVER WRITTEN TO ===
    reg_to_assign = {} 
    # Deal with consumer operands
    for instr_reading in parsedInstruction:
        if instr_reading['opcode'] == 'st':
            operands_type = ['dest', 'src1']
        else:
            operands_type = ['src1', 'src2']
        for field in operands_type:
            val = instr_reading[field]
            if val and val.startswith("x"):
                matches = []
                for instr_writting in parsedInstruction:
                    if (instr_writting['dest'] == instr_reading[field] and instr_writting != instr_reading):
                        matches.append(instr_writting['instrAddress'])
                        break
                if matches == []:
                    key = (instr_reading['instrAddress'], field)
                    reg_to_assign[key] = field
        for field in ['memSrc1', 'memSrc2']:
                val = instr_reading.get(field)
                if val and '(' in val:
                    matches = []
                    match = re.search(r'(x\d+)', val)
                    if match:
                        instr_reg = match.group(1)
                        for instr_writting in parsedInstruction:
                            if instr_reg == instr_writting['dest']:
                                matches.append(instr_writting['instrAddress'])
                                break
                        if matches == []:
                            key = (instr_reading['instrAddress'], field)
                            reg_to_assign[key] = field

    #print(reg_to_assign)
    # Deal with producer operands
    edge_instructions = parsedInstruction[:bb1_start+1]+parsedInstruction[bb2_start+1:]
    for instr_prod in edge_instructions:
        match = []
        if instr_prod['opcode'] not in ['BB0', 'BB1', 'BB2'] and instr_prod['opcode'] != 'st' and instr_prod['dest'] not in ['LC', 'EC']: # For None
            for instr_read in parsedInstruction:
                instr_prod_addr = instr_prod['instrAddress']
                instr_read_addr = instr_read['instrAddress']
                deps       = dep_map.get(instr_read_addr, {})
                for dep_list in (
                    deps.get('localDependency', []),
                    deps.get('interloopDep',   []),
                    deps.get('loopInvarDep',    []),
                    deps.get('postLoopDep',     []),
                ):
                    for producer_addr, dep_reg in dep_list:
                        if producer_addr == instr_prod_addr:
                            match.append(instr_read_addr)
                            break
            if match == []:
                key = (instr_prod_addr, 'dest')
                reg_to_assign[key] = 'dest'

    #print(reg_to_assign)

    free_regs = get_free_static(instructions)

    for entry in reg_to_assign:
        if entry[1] == 'dest':
            if entry[0] not in free_regs:
                #print(free_regs)
                instr = instr_map[entry[0]]
                free_regs.append(instr['dest'])
                free_regs.sort(key=lambda r: int(r[1:]))
                #print(free_regs)

    for instr in instructions:
        addr = instr.get('instrAddress')
        for field in ['dest', 'src1', 'src2']:
            if (addr, field) in reg_to_assign:
                #print(instr[field])
                instr[field] = 'x0'
        for field in ['memSrc1', 'memSrc2']:
            if (addr, field) in reg_to_assign:
                val = instr.get(field)
                if val and '(' in val:
                    match = re.search(r'(x\d+)', val)
                    if match:
                        offset, _, _ = val.partition('(') 
                        instr[field] = f"{offset}(x{0})"


    scheduled_instrs = [
        instr_id
        for bundle in schedule
        for instr_id in sorted(
            bundle['instructions'],
            key=lambda i: priority[get_unit_type(instr_map[i])]
        )
    ]

    for instr_addr in scheduled_instrs:
        instr = instr_map[instr_addr]
        for field in ['dest', 'src1', 'src2']:
            val = instr[field]
            if val == 'x0':
                original_reg = instr[field]
                instr[field] = free_regs[0]
                #print(f"[PHASE 4e: Rename never written to regiser] {free_regs[0]} @ field {field} and @ opcode {instr["opcode"]}")
                free_regs.pop(0)
                #print("=== FREE REGS===")
                #print(free_regs)
        for field in ['memSrc1', 'memSrc2']:
            val = instr.get(field)
            if val and '(' in val:
                matches = []
                match = re.search(r'(x\d+)', val)
                if match:
                    instr_reg = match.group(1)
                    if instr_reg == 'x0':
                        if field == 'memSrc1':
                            offset, _, _ = val.partition('(') 
                            instr[field] = f"{offset}({instr['src1']})"
                            #print(f"[PHASE 4e: Rename never written to regiser] {instr['src1']} @ field {field} and @ opcode {instr["opcode"]}")
                        else:
                            offset, _, _ = val.partition('(') 
                            instr[field] = f"{offset}({instr['src2']})"
                            #print(f"[PHASE 4e: Rename never written to regiser] {instr['src1']} @ field {field} and @ opcode {instr["opcode"]}")

    return 

def get_free_static(instructions):
        already_used_static = []
        for instr in instructions:
            for field in ['dest']:
                val = instr[field]
                if val and val.startswith("x"):
                    num = val[1:]
                    if num.isdigit() and 1 <= int(num) <= 31:
                        already_used_static.append(f'x{num}')

        already_used_static = set(already_used_static)
        static_reg = [f"x{i}" for i in range(1, 32)]

        free_regs = [r for r in static_reg if r not in already_used_static]

        return free_regs


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
                    operands_type = ['dest', 'src1']
                else:
                    operands_type = ['src1', 'src2']
                for field in operands_type:
                    if consumer_instr[field] == dep_reg:
                        original_dest = consumer_instr[field]
                        consumer_instr[field] = producer_reg
                        #print(f"[PHASE 3: Rename consumer due to loopInvar] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                for field in ['memSrc1', 'memSrc2']:
                    val = consumer_instr.get(field)
                    if val and '(' in val:
                        match = re.search(r'(x\d+)', val)
                        if match:
                            consumer_reg = match.group(1)
                            if consumer_reg == dep_reg:
                                offset, _, _ = val.partition('(') 
                                original_dest = consumer_reg
                                consumer_instr[field] = f"{offset}({producer_reg})"
                                #print(f"[PHASE 3: Rename consumer due to loopInvar] {original_dest} → {producer_reg} @ field {field} and @ opcode {consumer_instr["opcode"]}")
                       
    # === TREAT LOCAL DEPENDENCIES ===
            for producer_addr, dep_reg in deps.get('localDependency', []):
                producer_instr      = instr_map[producer_addr]

                producer_stage = math.floor(instr_pos_in_sch[producer_addr]/II)
                consumer_stage   = math.floor(instr_pos_in_sch[instr_addr]/II)

                increment = consumer_stage - producer_stage 

                if consumer_instr['opcode'] == 'st':
                    operands_type = ['dest', 'src1']
                else:
                    operands_type = ['src1', 'src2']
                for field in operands_type:
                    if consumer_instr[field] == dep_reg:
                        producer_reg = producer_instr['dest']
                        reg_num = int(producer_reg.lstrip('x'))
                        new_num = reg_num + increment
                        consumer_instr[field] = f"x{new_num}"
                        #print(f"[PHASE 3: Rename consumer due to localDep] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
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
                                offset, _, _ = val.partition('(') 
                                consumer_instr[field] = f"{offset}(x{new_num})"
                                #print(f"[PHASE 3: Rename consumer due to localDep] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    # === TREAT INTERLOOP ===
    
            for producer_addr, dep_reg in deps.get('interloopDep', []):
                producer_instr      = instr_map[producer_addr]

                if producer_addr not in instr_pos_in_sch.keys():
                    continue

                producer_stage = math.floor(instr_pos_in_sch[producer_addr]/II)
                consumer_stage   = math.floor(instr_pos_in_sch[instr_addr]/II)

                increment = consumer_stage - producer_stage + 1

                if consumer_instr['opcode'] == 'st':
                    operands_type = ['dest', 'src1']
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
                        #print(f"[PHASE 3: Rename consumer due to Interloop] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")
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
                                offset, _, _ = val.partition('(') 
                                consumer_instr[field] = f"{offset}(x{new_num})"
                                #print(f"[PHASE 3: Rename consumer due to Interloop] {dep_reg} → {f"x{new_num}"} @ field {field} and @ opcode {consumer_instr["opcode"]}")

    return first_point_phase_four


def phase_two(modulo_schedule, instructions, dependencyTable):
    static_reg = 1

    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable}

    already_renamed = set()


    # === FIND LOOP INVARIANCES ===
    for bundle in modulo_schedule:
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
                    #print(f"[PHASE 2: Rename producer] {original_dest} → {new_reg} @ instr {producer_addr}")
                    static_reg += 1
                    already_renamed.add(producer_addr)
                else:
                    # If has already been renamed get his renamed value
                    new_reg = producer_instr['dest']

    return


def phase_one(instructions, II, modulo_schedule):
    step = count_stages(modulo_schedule) + 1
    rotating_base = 32
    rename_count       = 0

    instr_map = {instr['instrAddress']: instr for instr in instructions}

    has_been_allocated_phase1 = {}
    # === SELECT INSTRUCTIONS TO ROTATE ===
    scheduled_instrs = [
        instr_id
        for bundle in modulo_schedule[:II]
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
        has_been_allocated_phase1[instr['instrAddress']] = new_reg

        #print(f"[PHASE 1: Rename dest] {original_dest} → {new_reg} @ instr {addr}")
        rename_count += step

    #print(has_been_allocated_phase1)
    return has_been_allocated_phase1
