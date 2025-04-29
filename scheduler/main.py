import sys
import json
from dependency_detector import detector
from scheduler_loop import simple_loop
from register_loop import register_loop

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
    
    for i in parsedInstruction:
        print(i)
    print("\n=== Dependency Table ===")
    for i in dependencyTable[0]:
        print(i)    
            
    
    dependencyTable = dependencyTable[0]
    loopScheduler = simple_loop(dependencyTable, parsedInstruction)
    print("\n=== Loop Scheduler ===")
    print_schedule(loopScheduler)
    (schedule, parsedInstruction) = register_loop(loopScheduler, parsedInstruction, dependencyTable)

    json2 = convert_loop_to_json(parsedInstruction, schedule)
    
    with open(outputLoop, "w") as f:
        json.dump(json2, f, indent=4)

    if debug_mode:
        for i in json2:
            print(i)


if __name__ == "__main__":
    main()