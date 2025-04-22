import re

from utils import parse_mem_operand
def detector(instruction):
    parsed_instruction = parse_instruction(instruction)
    
    
    dependency_analysis_result = dependency_analysis(parsed_instruction)
    return (parsed_instruction,dependency_analysis_result)

def parse_instruction(instruction):
    """
    Parses assembly instructions and returns dictionnary
    """
    decoded_instructions = []
    for idx, inst in enumerate(instruction):
        parts = inst.replace(",", "").split()
        opcode = parts[0]
        operands = parts[1:]

        while len(operands) < 3:
            operands.append(None)

        mem_src1 = parse_mem_operand(operands[1])
        mem_src2 = parse_mem_operand(operands[2])

        src1 = mem_src1["base"] if mem_src1 else operands[1]
        src2 = mem_src2["base"] if mem_src2 else operands[2]
        if mem_src1:
            mem_src1 = mem_src1["raw"]
        if mem_src2:
            mem_src2 = mem_src2["raw"]
        decoded_instructions.append({
            "instrAddress": idx,
            "opcode": opcode,
            "dest": operands[0],
            "src1": src1,
            "src2": src2,
            "memSrc1": mem_src1,
            "memSrc2": mem_src2,
        })

    whereToInsert = -1
    for idx , x in enumerate(decoded_instructions):
        if x["opcode"] == "loop":
            print("loop detected")
            decoded_instructions.insert(idx+1,{
                "instrAddress": -1,
                "opcode": "BB2",
                "dest": None,
                "src1": None,
                "src2": None
            })
            whereToInsert = x["dest"]
            print(whereToInsert)
            decoded_instructions.insert(int(whereToInsert),{
                "instrAddress": -1,
                "opcode": "BB1",
                "dest": None,
                "src1": None,
                "src2": None
            })
            break
    
    decoded_instructions.insert(0,{
        "instrAddress": -1,
        "opcode": "BB0",
        "dest": None,
        "src1": None,
        "src2": None
    })
    
    return decoded_instructions

def dependency_analysis(parsed):
    """
    Perform dependency analysis on the parsed instructions.
    """
    dependency_table = []
    for i in range(len(parsed)):
        dependency_table.append({"instrAddr": parsed[i]["instrAddress"], "localDependency": [], "interloopDep": [], "loopInvarDep" : [],"postLoopDep": []})
    detect_local_dependencies(parsed, dependency_table)
    detect_interlop_dependencies(parsed, dependency_table)
    return dependency_table

def detect_local_dependencies(parsed, dependency_table):
    """
    Detect local dependencies within the same block.
    """
    currentBlock = "BB0"
    for i in range(len(parsed)):
        if parsed[i]["instrAddress"] == -1:
            currentBlock = parsed[i]["opcode"]
            continue
        
        newBlock = "BB0"
        for j in range(i):
            if parsed[j]["instrAddress"] == -1:
                newBlock = parsed[j]["opcode"]
                continue
            if (parsed[j]["dest"] == parsed[i]["src1"] or parsed[j]["dest"] == parsed[i]["src2"]) and currentBlock == newBlock and parsed[j]["dest"] != None:
                dependency_table[i]["localDependency"].append(parsed[j]["instrAddress"])
                
def detect_interlop_dependencies(parsed, dependency_table):
    """
    Detect interloop in different blocks or iteration.
    """
    #First we do for different block
    currentBlock = "BB0"
    for i in range(len(parsed)):
        if parsed[i]["instrAddress"] == -1:
            currentBlock = parsed[i]["opcode"]
            continue
        if currentBlock != "BB1":
            continue
        newBlock = "BB0"
        toAdd1 = -1
        toAdd2 = -1
        print(f"currentBlock: {currentBlock} instrAddress: {parsed[i]['instrAddress']}")
        for j in range(len(parsed)):
            if parsed[j]["instrAddress"] == -1:
                newBlock = parsed[j]["opcode"]
                continue
            if (parsed[j]["dest"] == parsed[i]["src1"] or parsed[j]["dest"] == parsed[i]["src2"]):
                match newBlock:
                    case "BB0":
                            toAdd1 = parsed[j]["instrAddress"]
                            continue
                    case "BB1":
                            print(f"BB1: {parsed[j]['instrAddress']} {parsed[i]['instrAddress']}")
                            if (parsed[j]["instrAddress"]>=parsed[i]['instrAddress']):
                                toAdd2 = parsed[j]["instrAddress"]
                            continue
                    case "BB2":
                        break
        print(f"toAdd1: {toAdd1} toAdd2: {toAdd2}")
        if toAdd2 != -1:
            dependency_table[i]["interloopDep"].append(toAdd2)
            if toAdd1 != -1:
                dependency_table[i]["interloopDep"].append(toAdd1)
    