import sys
import json

from dependency_detector import detector
def main():
    if len(sys.argv) != 4:
        print("Error use the following command: python simulator.py input.json outputLoop.json outputLoopPip.json")
        return
    input = sys.argv[1]
    outputLoop = sys.argv[2]
    outputLoopPip = sys.argv[3]
    # Load input
    print("Loading input file...")
    with open(input) as f:
        instructions = json.load(f)
        
    (parserInstruction, dependencyTable) = detector(instructions)   
    
    for x in parserInstruction:
        print(x)
    
    for x in dependencyTable:
        print(x)
if __name__ == "__main__":
    main()