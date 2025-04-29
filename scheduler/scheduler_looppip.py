from utils import *
from scheduler_loop import *

def pip_loop(dependencyTable, instructions):
    """
    Simulates a loop pipelined (loop.pip) scheduler.
    
    Args:
        dependencyTable (dict).
        instructions (list).
    
    Returns:
        list: List of scheduled instructions across BB0, BB1, and BB2.
    """
    
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
    scheduleBB1 = schedule_loop(instructions[bb1_start+1:bb2_start], dependencyTable, unit_limit, II)
    add_delay_BB0_dependency(scheduleBB0, scheduleBB1, dependencyTable, instructions)
    
    # Schedule BB2 
    scheduleBB2 = schedule_basic_block(instructions[bb2_start+1:], dependencyTable, unit_limit, instructions) if bb2_start else []
    add_delay_BB2_dependency(scheduleBB1,scheduleBB2, dependencyTable, instructions)
    
    return scheduleBB0 + scheduleBB1 + scheduleBB2



def schedule_loop(block_instr, dependencyTable, unit_limit, II):
    """
    Schedules instructions of a loop block based on "loop.pip" instruction based on resource availability and dependencies.
    
    Args:
        loop_instr (list): List of instructions belonging to the loop block to be scheduled.
        dependency_table (dict).
        unit_limit (dict)..
        full_instr (list): Complete list of all parsed instructions (to resolve global indices).
    
    Returns:
        list: List of scheduled bundles for the loop body.
    """

    schedule = basic_schedule(block_instr, dependencyTable, unit_limit)

    if(False == test_ii(block_instr, schedule, dependencyTable, II)):
        print("Need to redo schedule with increased II")
        II += 1
        return schedule_loop(block_instr, dependencyTable, unit_limit, II)

    print("II is:", II)

    # Schedule function now using the basic schedule + II value
    schedule =  complex_schedule(schedule, II)

    return schedule

def complex_schedule(basic_sch, II):
    complex_sch = [init_bundle() for _ in range(len(basic_sch))]

    while len(complex_sch) % II != 0:
        complex_sch.append(init_bundle())

    print(complex_sch)

    # Add the branch (last instruction in the last bundle of basic and also add BRANCH +1)

    return complex_sch

def basic_schedule(block_instr, dependencyTable, unit_limit):
    """
    Basic instruction scheduling without interloop constraint validation.
    
    Args:
        block_instr (list): Instructions of the loop block to schedule.
        dependencyTable (list): Dependency info per instruction.
        unit_limit (dict): Available resource units per operation type.
    
    Returns:
        list: List of scheduled bundles.
    """
    schedule = [init_bundle()]  # Start with one bundle

    for instr in block_instr[:-1]:  # Skip the branch for now
        op_class = get_unit_type(instr)

        # Find matching dependency entry
        matching_dep = next((dep for dep in dependencyTable if dep['instrAddress'] == instr['instrAddress']), None)

        latency = 0
        scheduled = False
        i = 0  # Bundle index

        while not scheduled:
            if i >= len(schedule):
                schedule.append(init_bundle())  # Dynamically add a new bundle if needed

            bundle = schedule[i]

            if latency > 0:
                latency -= 1
                i += 1
                continue

            if bundle[op_class] < unit_limit[op_class]:  # Resource availability check
                conflict = False

                if matching_dep:
                    for dep_type in ["localDependency", "interloopDep"]:
                        for (dep_instr_addr, _) in matching_dep.get(dep_type, []):
                            if dep_instr_addr in bundle['instructions']:
                                # Check if dependency has mulu latency
                                for dep_instr in block_instr:
                                    if dep_instr['instrAddress'] == dep_instr_addr:
                                        if dep_instr['opcode'] == "mulu":
                                            latency += 2
                                        break
                                conflict = True
                                break

                if conflict:
                    i += 1
                    continue

                # No conflict and resources available: schedule it
                bundle['instructions'].append(instr['instrAddress'])
                bundle[op_class] += 1
                scheduled = True
            else:
                i += 1  # Try next bundle

    # Finally, schedule the branch instruction
    schedule[-1]['instructions'].append(block_instr[-1]['instrAddress'])
    schedule[-1]["BRANCH"] += 1

    print("====Schedule=====")
    print(schedule)

    return schedule


def test_ii(block_instr, schedule, dependencyTable, II):

    report = []

    # For easy access
    instr_map = {instr['instrAddress']: instr for instr in block_instr}

    for bundle_idx, bundle in enumerate(schedule):
        for instr_addr in bundle['instructions']:
            # Get full instruction being tested
            instr = instr_map[instr_addr]

            # Find matching dependency entry
            matching_dep = next((dep for dep in dependencyTable if dep['instrAddress'] == instr_addr), None)

            if matching_dep:
                for (dep_instr_addr, dep_latency) in matching_dep.get('interloopDep', []):
                    dependent_bundle_idx = find_bundle_of_instr(dep_instr_addr, schedule)
                    if dependent_bundle_idx is not None:
                        dependent_instr = instr_map[dep_instr_addr]
                        dependent_opcode = dependent_instr['opcode']

                        report.append({
                            'dependent_bundle_idx': dependent_bundle_idx,
                            'dependent_opcode': dependent_opcode,
                            'current_bundle_idx': bundle_idx,
                        })
    print("======Report=====")
    print(report)
    
    for test in report:
        latency = 3 if test['dependent_opcode'] == "mulu" else 1

        if test['dependent_bundle_idx'] + latency <= test['current_bundle_idx'] + II:
            print("Test passed")
        else:
            print("Test failed")
            return False

    return True

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

    return max(ii_values)





