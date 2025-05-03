import sys
import json
from dependency_detector import detector
from scheduler_loop import simple_loop
from scheduler_looppip import pip_loop
from register_loop import register_loop
from register_looppip import pip_register

from utils import *
def main():
    args = sys.argv[1:]

    if len(args) < 3 or len(args) > 4:
        raise ValueError("Usage: python main.py input.json outputLoop.json outputLoopPip.json [--debug]")


    input = args[0]
    outputLoop = args[1]
    outputLoopPip = args[2]
    debug_mode = False

    if len(args) == 4:
        if args[3] == "--debug":
            debug_mode = True
        else:
            print(f"Unknown option {args[3]}")
            return

    with open(input) as f:
        instructions = json.load(f)
    
    # Dependency detection & Parsing
    (parsedInstruction, dependencyTable) = detector(instructions)

    print("\n=== Dependency Table ===")
    for entry in dependencyTable[0]:
        print(entry)

    print("\n=== Parsed Instructions ===")
    for entry in parsedInstruction:
        print(entry)
            
    dependencyTable = dependencyTable[0]

    # Scheduling
        # Classic
    loopScheduler = simple_loop(dependencyTable, parsedInstruction)
    print_schedule(loopScheduler)

        # Pip
    schedule, loopSchedule, II, non_modulo = pip_loop(dependencyTable, parsedInstruction)
    print("\n=== Loop.pip Scheduler ===")
    print_schedule(schedule)

    # Register renaming
        # Classic
    (schedule, parsedInstruction) = register_loop(loopScheduler, parsedInstruction, dependencyTable)

        # Pip
    # cause crash    
    parsedInstruction = pip_register(schedule, loopSchedule, parsedInstruction, II, dependencyTable, non_modulo)

    print("====Register Allocation====")
    for entry in parsedInstruction:
        print(entry)

    # Convert to final format
        # Classic
    json2 = convert_loop_to_json(parsedInstruction, schedule)

    with open(outputLoop, "w") as f: 
        json.dump(json2, f, indent=4)

        # Pip
    # cause crash
    clean_instructions(parsedInstruction)

    print("\n=== Cleaned Instructions ===")
    for entry in parsedInstruction:
        print(entry)

    json_schedule = form_json(parsedInstruction, schedule)

    print("\n=== Cleaned Schedule ===")
    for entry in json_schedule:
        print(entry)

    json_schedule = loop_prep(json_schedule)

    print("\n=== Loop prep Schedule ===")
    for entry in json_schedule:
        print(entry)

    json_schedule = insert_movs(json_schedule, II)
    print("\n=== Loop prep Schedule ===")
    for entry in json_schedule:
        print(entry)

    json_schedule = adjust_loop_address(json_schedule, II)
    print("\n=== Loop prep Schedule ===")
    for entry in json_schedule:
        print(entry)

    json_schedule = generate_predicates(json_schedule, non_modulo)
    print("\n=== Loop prep Schedule ===")
    for entry in json_schedule:
        print(entry)
    
    with open(outputLoopPip, "w") as f:
        json.dump(json_schedule, f, indent=4)


if __name__ == "__main__":
    main()