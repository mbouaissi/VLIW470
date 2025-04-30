from utils import *
def pip_register(schedule, loopSchedule, instructions, II, dependencyTable):

    stride = II

    instructions = phase_one(loopSchedule, instructions, stride)

    instructions = phase_two(loopSchedule, instructions, dependencyTable)

    instructions = phase_three(loopSchedule, instructions, dependencyTable)

    return instructions

def phase_three(loopSchedule, instructions, dependencyTable):

    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map = {entry['instrAddress']: entry for entry in dependencyTable}

    for bundle in loopSchedule:
        for instr_addr in bundle['instructions']:

            # Get dependency info for this instruction
            deps = dep_map.get(instr_addr, {})



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
                    print("We rewrite a consumer reg")                  
                if consumer_instr.get('memSrc1') == producer_reg:    
                    consumer_instr['memSrc1'] = new_reg            
                if consumer_instr.get('memSrc2') == producer_reg:    
                    consumer_instr['memSrc2'] = new_reg


    return instructions

def phase_one(loopSchedule, instructions, stride):

    rotating_base = 32
    rename_count = 0

    # Order the instructions for renaming
    instr_map = {instr['instrAddress']: instr for instr in instructions}
    scheduled_instrs = [
        instr_id
        for bundle in loopSchedule[:stride]
        for instr_id in sorted(
            bundle['instructions'],
            key=lambda i: priority[get_unit_type(instr_map[i])]
        )
    ]

    for idx in scheduled_instrs:
        instr = instr_map[idx]

        if instr['opcode'] in ('st', 'loop') or instr['dest'] in ('LC', 'EC'):
            continue
        else:
            instr['dest'] = f'x{rotating_base + rename_count}'
            rename_count += stride

    return instructions
