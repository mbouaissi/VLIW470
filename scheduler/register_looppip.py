from utils import *
def pip_register(schedule, loopSchedule, instructions, II, dependencyTable):

    stride = II

    instructions = phase_one(loopSchedule, instructions, stride)

    instructions = phase_two(loopSchedule, instructions, dependencyTable)

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

            # Get dependency info for this instruction
            deps = dep_map.get(instr_addr, {})
            loop_invariant_deps = deps.get('loopInvarDep', [])

            # Loop through all loop-invariant dependencies (tuples) and get the address of their dependence
            for producer_addr, _ in loop_invariant_deps:

                if producer_addr in already_renamed:
                    continue  # Skip if already renamed
                
                # Assign a new static register: x1, x2, ...
                producer_instr = instr_map.get(producer_addr)
                new_reg = f"x{static_base + static_counter}"
                producer_instr['dest'] = new_reg
                static_counter += 1
                already_renamed.add(producer_addr)


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
