from utils import *
def pip_register(schedule, loopSchedule, instructions, II):

    stride = II

    instructions = phase_one(loopSchedule, instructions, stride)
    return instructions




def phase_one(loopSchedule, instructions, stride):

    rotating_base = 32
    rename_count = 0

    # Order the instructions for renaming
    instr_map = {instr['instrAddress']: instr for instr in instructions}
    scheduled_instrs = [
    instr
    for bundle in loopSchedule[:stride]
    for instr in sorted(
        bundle['instructions'],
        key=lambda i: priority[get_unit_type(instr_map[i])]
    )
]

    for idx in scheduled_instrs:
        instr = instr_map[idx] 

        if (instr['opcode'] in ('st', 'loop')) or (instr['dest'] in ('LC', 'EC')):
            continue
        else:
            instr['dest'] = 'x' + str(rotating_base + rename_count)
            rename_count += stride

    return instructions
