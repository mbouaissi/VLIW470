from utils import *
from scheduler_loop import *
import math
import copy

def pip_loop(dependencyTable, instructions):
    print("====START====")
    scheduleBB0 = []
    scheduleBB1 = []
    scheduleBB2 = []

    bb1_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB1"), len(instructions))
    bb2_start = next((i for i, instr in enumerate(instructions) if instr["opcode"] == "BB2"), None)

    # Schedule BB0 
    scheduleBB0 = schedule_basic_block(instructions[:bb1_start], dependencyTable, unit_limit, instructions)
    
    if bb1_start == len(instructions):
        return scheduleBB0
    
    # Schedule BB1
    II = bounded_ii(instructions[bb1_start+1:bb2_start])
    print("BOUND II", II)
    scheduleBB1, II, non_modulo = schedule_loop(instructions[bb1_start+1:bb2_start], dependencyTable, unit_limit, II)
    # scheduleBB1 is the modulo schedule

    add_delay_BB0_dependency(scheduleBB0, scheduleBB1, dependencyTable, instructions)
    modulo_schedule = copy.deepcopy(scheduleBB1)
    
    # Schedule BB2 
    scheduleBB2 = schedule_basic_block(instructions[bb2_start+1:], dependencyTable, unit_limit, instructions) if bb2_start else []
    add_delay_BB2_dependency(non_modulo,scheduleBB2, dependencyTable, instructions)
    
    return scheduleBB0 + scheduleBB1 + scheduleBB2, II, modulo_schedule, non_modulo


def schedule_loop(block_instr, dependencyTable, unit_limit, II):

    basic_sch = basic_schedule(block_instr, dependencyTable, unit_limit)

    print("===END OF BASIC SCHEDULE===")
    print_schedule(basic_sch)

    accepted_II = False

    while (accepted_II == False):
        mod_schedule, non_mod_schedule =  complex_schedule(basic_sch, block_instr, II)
        need_higher_II = test_ii(block_instr, mod_schedule, dependencyTable, II)

        if need_higher_II == False:
            print("passed with II:", II)
            accepted_II = True
        else:
            print("II not sufficient", II)
            II += 1
    
    print("Accepted II is:", II)
    print("===Schedule===")
    print_schedule(basic_sch)
    print("===Modulo Schedule===")
    print_schedule(mod_schedule)
    print("===Non modulo schedule===")
    print_schedule(non_mod_schedule)

    return mod_schedule, II, non_mod_schedule

def complex_schedule(basic_sch, block_instr, II):

    print("===START COMPLEX===")
    print(II)
    # Initializaton
    schedule = basic_sch
    schedule[-1]['instructions'].pop()
    schedule[-1]["BRANCH"] = 0

    while len(schedule) % II != 0:
        schedule.append(init_bundle())

    mod_schedule = [init_bundle() for _ in range(len(schedule))]
    instr_map = {instr["instrAddress"]: instr for instr in block_instr}

    for idx, bundle in enumerate(schedule):
        for instr in bundle['instructions']:
            repeat_idx = idx % II
            op_class = get_unit_type(instr_map[instr])

            while(repeat_idx < len(schedule)):
                if mod_schedule[repeat_idx][op_class] >= unit_limit[op_class]:
                    repeat_idx += 1
                else:
                    mod_schedule[repeat_idx]['instructions'].append(instr)
                    mod_schedule[repeat_idx][op_class] += 1
                    repeat_idx += II


    for idx, bundle in enumerate(mod_schedule):
        if ((idx + 1) % II == 0):
            mod_schedule[idx]['instructions'].append(block_instr[-1]['instrAddress'])
            mod_schedule[idx]["BRANCH"] += 1

    schedule[-1]['instructions'].append(block_instr[-1]['instrAddress'])
    schedule[-1]["BRANCH"] += 1


    print("===DEBUG SCH")
    print_schedule(mod_schedule)
    print_schedule(schedule)

    return mod_schedule, schedule



def basic_schedule(instructions, dependencyTable, unit_limit):
    schedule = [init_bundle() for _ in range(10)]

    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable}

    instr_to_bundle = update_instr_to_bundle(schedule)
    

    for instr in instructions[:-1]:
        bundle_idx = 0
        instr_addr = instr['instrAddress']
        instr_unit = get_unit_type(instr)
        deps   = dep_map.get(instr_addr, {})
        producer_dep = deps.get('localDependency')
        if producer_dep != []:
            for producer_addr, dep_reg in producer_dep:
                producer_instr = instr_map[producer_addr]
                if producer_instr['opcode'] == 'mulu':
                    bundle_idx = instr_to_bundle[producer_addr] + 3
                else:
                    bundle_idx = instr_to_bundle[producer_addr] + 1
                scheduled = False
                while (scheduled == False):
                    producer_instr = instr_map[producer_addr]
                    if schedule[bundle_idx][instr_unit] >= unit_limit[instr_unit]:
                        schedule.append(init_bundle())
                        bundle_idx += 1
                    else:
                        schedule[bundle_idx]['instructions'].append(instr_addr)
                        schedule[bundle_idx][instr_unit] += 1
                        scheduled = True
                        instr_to_bundle = update_instr_to_bundle(schedule)
        else:
            scheduled = False
            while (scheduled == False):
                if schedule[bundle_idx][instr_unit] >= unit_limit[instr_unit]:
                    schedule.append(init_bundle())
                    bundle_idx += 1
                else:
                    schedule[bundle_idx]['instructions'].append(instr_addr)
                    schedule[bundle_idx][instr_unit] += 1
                    scheduled = True
                    instr_to_bundle = update_instr_to_bundle(schedule)


    while schedule[-1]['instructions'] == []:
        schedule.pop()
    schedule[-1]['instructions'].append(instructions[-1]['instrAddress'])
    schedule[-1]['BRANCH'] += 1


    return schedule



def test_ii(instructions, schedule, dependencyTable, II):
    print("TEST II", II)
    print_schedule(schedule)

    instr_to_bundle = update_instr_to_bundle(schedule)
    instr_map = {instr['instrAddress']: instr for instr in instructions}
    dep_map   = {entry['instrAddress']: entry for entry in dependencyTable} 

    need_higher_II = False
    
    # for instr in instructions:
    #     instr_addr = instr['instrAddress']
    #     deps   = dep_map.get(instr_addr, {})
    #     producer_dep = deps.get('localDependency')
    #     for producer_addr, dep_reg in producer_dep:
    #         producer_instr = instr_map[producer_addr]
    #         producer_idx = instr_to_bundle[producer_addr]
    #         consumer_idx = instr_to_bundle[instr_addr]

    #         if producer_instr['opcode'] == 'mulu':
    #             if (producer_idx + 3 > consumer_idx + II):
    #                 print("CAUSE OF HIGHER: ", producer_dep)
    #                 need_higher_II = True
    #         else:
    #             if (producer_idx + 1 > consumer_idx + II):
    #                 print("CAUSE OF HIGHER: ", producer_dep)
    #                 need_higher_II = True

    # print("AFTER LOCAL DEP: ", need_higher_II)

    for instr in instructions:
        instr_addr = instr['instrAddress']
        deps   = dep_map.get(instr_addr, {})
        producer_dep = deps.get('interloopDep')
        for producer_addr, dep_reg in producer_dep:
            if producer_addr in instr_to_bundle.keys():
                producer_instr = instr_map[producer_addr]
                producer_idx = instr_to_bundle[producer_addr]
                consumer_idx = instr_to_bundle[instr_addr]

                if producer_instr['opcode'] == 'mulu':
                    if (producer_idx + 3 > consumer_idx + II):
                        print("CAUSE OF HIGHER: ", producer_dep, producer_addr)
                        need_higher_II = True
                else:
                    if (producer_idx + 1 > consumer_idx + II):
                        need_higher_II = True
                        print("CAUSE OF HIGHER: ", producer_dep, producer_addr)

    return need_higher_II

# Do the inequation to find about the correct II value



def bounded_ii(instructions):
    """
    Finds the minimal II allowing a valid ASAP schedule.
    
    Args:
        instructions (list): List of instruction objects.
        dependency_table (dict).
        initial_II (int).
        
    Returns:
        int: Minimal valid II.
    """
    op_counts = count_operations_per_class(instructions)
    ii_values = []

    for op_class, num_operations in op_counts.items():
        units = unit_limit[op_class]
        ii_values.append((num_operations / units))

    return int(math.ceil(max(ii_values)))





