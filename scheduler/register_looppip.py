from utils import *
import math

def pip_register(schedule, loopSchedule, instructions, II, dependencyTable, non_modulo):

    stride = II

    instructions = phase_one(loopSchedule, instructions, stride)

    instructions = phase_two(loopSchedule, instructions, dependencyTable)

    instructions = phase_three(loopSchedule, instructions, dependencyTable, stride, non_modulo)

    return instructions

def phase_three(loopSchedule, instructions, dependencyTable, stride, non_modulo):

    instr_to_bundle = {
        instr_id: bundle_idx
        for bundle_idx, bundle in enumerate(non_modulo)
        for instr_id in bundle['instructions']
    }
    print(instr_to_bundle)

    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map = {entry['instrAddress']: entry for entry in dependencyTable}

    for bundle in non_modulo:
        for instr_addr in bundle['instructions']:

            # Get dependency info for this instruction
            # Loop invariant dependencies are treated in phase 2
            deps = dep_map.get(instr_addr, {})
            # To account for stage offset (see blue in HW pdf)
            for producer_addr, reg in deps.get('localDependency', []):
                bundle_idx_consumer = instr_to_bundle[instr_addr]
                bundle_idx_producer = instr_to_bundle[producer_addr]

                increment = math.floor((bundle_idx_consumer - bundle_idx_producer)/(stride))
                print(increment)
                
                consumer_instr = instr_map.get(instr_addr)
                producer_instr = instr_map.get(producer_addr)

                reg = producer_instr['dest']

                # Standard source operands
                for field in ['src1', 'src2']:
                    if consumer_instr.get(field) == reg:
                        old_reg_val = consumer_instr[field]
                        new_reg = f"x{int(old_reg_val[1:]) + increment}"
                        consumer_instr[field] = new_reg
                        print(f"[Update] Instr {instr_addr}: field '{field}' changed from {old_reg_val} to {new_reg}")

                # Destination operand (for store dependencies)
                if consumer_instr['opcode'] == 'st' and consumer_instr.get('dest') == reg:
                    old_reg_val = consumer_instr['dest']
                    new_reg = f"x{int(old_reg_val[1:]) + increment}"
                    consumer_instr['dest'] = new_reg
                    print(f"[Update] Instr {instr_addr}: field 'dest' changed from {old_reg_val} to {new_reg}")

                # Memory source fields
                for mem_field in ['memSrc1', 'memSrc2']:
                    mem_val = consumer_instr.get(mem_field)
                    if mem_val and f"({reg})" in mem_val:
                        new_reg = f"x{int(reg[1:]) + increment}"
                        updated_mem_val = mem_val.replace(f"({reg})", f"({new_reg})")
                        consumer_instr[mem_field] = updated_mem_val
                        print(f"[Update] Instr {instr_addr}: field '{mem_field}' changed from {mem_val} to {updated_mem_val}")

            

            # To account for iteration offset (see red in HW pdf)
            for producer_addr, reg in deps.get('interloopDep', []):
                if producer_addr in instr_to_bundle:
                    print("producer_addr is:", producer_addr)
                    bundle_idx_consumer = instr_to_bundle[instr_addr]
                    bundle_idx_producer = instr_to_bundle[producer_addr]

                    increment = math.floor(((bundle_idx_consumer - bundle_idx_producer)/(stride))+1)
                    print("increment regarding interloopDep", increment)
                    
                    consumer_instr = instr_map.get(instr_addr)
                    print("Consumer instr is:", consumer_instr)
                    producer_instr = instr_map.get(producer_addr)

                    reg = producer_instr['dest']

                    # Standard source operands
                    for field in ['src1', 'src2']:
                        if consumer_instr.get(field) == reg:
                            old_reg_val = consumer_instr[field]
                            new_reg = f"x{int(old_reg_val[1:]) + increment}"
                            consumer_instr[field] = new_reg
                            print(f"[Update] Instr {instr_addr}: field '{field}' changed from {old_reg_val} to {new_reg}")

                    # Destination operand (for store dependencies)
                    if consumer_instr['opcode'] == 'st' and consumer_instr.get('dest') == reg:
                        old_reg_val = consumer_instr['dest']
                        new_reg = f"x{int(old_reg_val[1:]) + increment}"
                        consumer_instr['dest'] = new_reg
                        print(f"[Update] Instr {instr_addr}: field 'dest' changed from {old_reg_val} to {new_reg}")

                    # Memory source fields
                    for mem_field in ['memSrc1', 'memSrc2']:
                        mem_val = consumer_instr.get(mem_field)
                        if mem_val and f"({reg})" in mem_val:
                            new_reg = f"x{int(reg[1:]) + increment}"
                            updated_mem_val = mem_val.replace(f"({reg})", f"({new_reg})")
                            consumer_instr[mem_field] = updated_mem_val
                            print(f"[Update] Instr {instr_addr}: field '{mem_field}' changed from {mem_val} to {updated_mem_val}")
            



    return instructions

def phase_two(loopSchedule, instructions, dependencyTable):

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

            for producer_addr, producer_reg in loop_invariant_deps:  
                producer_instr = instr_map.get(producer_addr)                                            

                if producer_addr not in already_renamed:
                    new_reg = f"x{static_base + static_counter}"
                    producer_instr['dest'] = new_reg
                    static_counter += 1
                    already_renamed.add(producer_addr)
                else:                                                
                    new_reg = producer_instr['dest']                 

                # Update operands in consumer that matched the original producer reg
                if consumer_instr.get('src1') == producer_reg:       
                    consumer_instr['src1'] = new_reg             
                if consumer_instr.get('src2') == producer_reg:       
                    consumer_instr['src2'] = new_reg                
                if consumer_instr.get('memSrc1') == producer_reg:    
                    consumer_instr['memSrc1'] = new_reg            
                if consumer_instr.get('memSrc2') == producer_reg:    
                    consumer_instr['memSrc2'] = new_reg

    return instructions

def phase_one(loopSchedule, instructions, stride):
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

    # Place rotating registers
    for idx in scheduled_instrs:
        instr = instr_map[idx]

        if instr['opcode'] in ('st', 'loop') or instr['dest'] in ('LC', 'EC'):
            continue

        original_dest = instr['dest']
        new_reg = f'x{rotating_base + rename_count}'
        instr['dest'] = new_reg
        reg_rename_map[original_dest] = new_reg
        rename_count += stride

    # Propagate changes to other registers
    for instr in instructions:
        # Update dest registers
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
    return instructions


