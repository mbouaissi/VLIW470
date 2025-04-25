import sys
import json
from dependency_detector import detector
from scheduler_loop import simple_loop
from register_loop import register_loop

from utils import print_schedule, format_instructions_schedule
def main():
    args = sys.argv[1:]

    if len(args) < 3 or len(args) > 4:
        print("Usage: python simulator.py input.json outputLoop.json outputLoopPip.json [--debug]")
        return

    debug_mode = False
    if "--debug" in args:
        debug_mode = True
        args.remove("--debug")

    input = args[0]
    outputLoop = args[1]
    outputLoopPip = args[2]

    # Load input
    if debug_mode:
        print("Debug mode enabled.")

    with open(input) as f:
        instructions = json.load(f)
        
    (parsedInstruction, dependencyTable) = detector(instructions)   
    if debug_mode:
        print("Parsed Instructions:")
        for x in parsedInstruction:
            print(x)
        print("Dependency Table:")
        for x in dependencyTable:
            print(x)
    loopScheduler = simple_loop(dependencyTable, parsedInstruction)    
    if debug_mode:
        print_schedule(loopScheduler)
    
    loopRegister = register_loop(loopScheduler, parsedInstruction, dependencyTable)
    
    (parsedInstruction, dependencyTable) = detector(loopRegister, needToParse=False)   
    loopScheduler = simple_loop(dependencyTable, parsedInstruction)    
    if debug_mode:
            print_schedule(loopScheduler)
    # if debug_mode:
    #     result = format_instructions_schedule(loopRegister)
    #     for line in result:
    #         print(line)
    


if __name__ == "__main__":
    main()