import sys
import json
from dependency_detector import detector
from scheduler_loop import simple_loop

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
def print_schedule(schedule):
    print("\n=== Simple Loop Schedule ===")
    for cycle, bundle in enumerate(schedule):
        print(f"Cycle {cycle}:")
        for unit in ["ALU", "MULT", "MEM", "BRANCH"]:
            count = bundle[unit]
            if count > 0:
                print(f"  {unit:<6}: {count} slot(s)")
        print(f"  Instructions: {bundle['instrs']}")
    print("===========================\n")


if __name__ == "__main__":
    main()