import sys
import json
import copy
from dependency_detector import detector
from scheduler_loop import simple_loop
from scheduler_looppip import pip_loop
from register_loop import register_loop
from register_looppip import pip_register
from pip_prep import *

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

    print("====Dependency detection & Parsing====")
    print("=== Dependency Table ===")
    for entry in dependencyTable[0]:
        print(entry)

    print("=== Parsed Instructions ===")
    for entry in parsedInstruction:
        print(entry)
            
    dependencyTable = dependencyTable[0]

    classic_instructions = copy.deepcopy(parsedInstruction)
    classic_dependencies= copy.deepcopy(dependencyTable)

    pip_instructions = copy.deepcopy(parsedInstruction)
    pip_dependencies = copy.deepcopy(dependencyTable)

    classic_processing(classic_instructions, classic_dependencies, outputLoop)

    # Use classic processing by default in case there isn't any loop
    if any(instr.get('opcode') == 'loop' for instr in pip_instructions):
        pip_processing(pip_instructions, pip_dependencies, outputLoopPip)
    else:
        classic_processing(classic_instructions, classic_dependencies, outputLoopPip)



def classic_processing(classic_instructions, classic_dependencies, outputLoop):
    classic_schedule = simple_loop(classic_dependencies, classic_instructions) # Scheduling
    (classic_schedule, classic_instructions) = register_loop(classic_schedule, classic_instructions, classic_dependencies) # Register renaming
    json2 = convert_loop_to_json(classic_instructions, classic_schedule) # Loop preparation

    with open(outputLoop, "w") as f: 
        json.dump(json2, f, indent=4)


def pip_processing(pip_instructions, pip_dependencies, outputLoopPip):
    pip_schedule, looppip_schedule, II, modulo_schedule, non_modulo_schedule = pip_loop(pip_dependencies, pip_instructions) # Scheduling
    pip_instructions = pip_register(pip_schedule, looppip_schedule, pip_instructions, II, pip_dependencies, non_modulo_schedule, modulo_schedule) # Register renaming
    json_schedule = pip_prep(pip_instructions, pip_schedule, II, non_modulo_schedule, modulo_schedule) # Loop prep

    print("===Final pip schedule===")
    print_schedule(json_schedule)


    with open(outputLoopPip, "w") as f:
        json.dump(json_schedule, f, indent=4)


if __name__ == "__main__":
    main()
