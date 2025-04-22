import copy

from .stage0 import fetch_and_decode
from .stage1 import rename_and_dispatch
from .stage2 import issue
from .stage34 import execute
from .stage5 import commit

def pipeline(state, instructions, trace):

    DIR = [] # Decoded Instruction Register
    ExecuteBuffer = [[],[]] # From issue → execute

    counter = 1

    while (
        state["PC"] < len(instructions)
        or state["DecodedPCs"]
        or state["ActiveList"] 
    ):
    # === Stage 5: Commit
        exception = commit(state)
        if exception:
            break

        # === Stage 3 & 4: Execute
        execute(state, ExecuteBuffer[1])
        ExecuteBuffer.pop()  # shift pipeline
        ExecuteBuffer.insert(0, []) # make room for next exec0


        # === Stage 2: Issue
        issued = issue(state)
        ExecuteBuffer[0].extend(issued)



        # === Stage 1: Rename & Dispacth
        DIR = rename_and_dispatch(state, DIR)

        # === Stage 0: Fetch & Decode
        if not DIR: 
            decoded = fetch_and_decode(state, instructions)
            DIR.extend(decoded)
        if DIR:
            state["DecodedPCs"] = [inst["PC"] for inst in DIR]


        # add new cycle to ouput
        trace.append(copy.deepcopy(state))

        print(f"Cycle: {counter}")
        print(f"IQ: {len(state['IntegerQueue'])}")
        print(f"Leftover: {DIR}")
        counter += 1

    return