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
        
    (parsedInstruction, dependencyTable) = detector(instructions)

    print("\n=== Dependency Table ===")
    for entry in dependencyTable[0]:
        print(entry)

    print("\n=== Parsed Instructions ===")
    for entry in parsedInstruction:
        print(entry)
            
    
    dependencyTable = dependencyTable[0]

    schedule, loopSchedule, II, non_modulo = pip_loop(dependencyTable, parsedInstruction)
    print("\n=== Loop.pip Scheduler ===")
    print_schedule(schedule)
    
    parsedInstruction = pip_register(schedule, loopSchedule, parsedInstruction, II, dependencyTable, non_modulo)

    print("====Register Allocation====")
    for entry in parsedInstruction:
        print(entry)

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

    # with open(outputLoopPip, "w") as f:
    #     json.dump(output_json, f, indent=4)

    # if debug_mode:
    #     for i in output_json:
    #         print(i)

if __name__ == "__main__":
    main()