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

        # Ensure we have 3 operands: dest, src1, src2
        while len(operands) < 3:
            operands.append(None)

        decoded_instructions.append({
            "instrAddress": idx,
            "opcode": opcode,
            "dest": operands[0],
            "src1": operands[1],
            "src2": operands[2]
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
                
    return dependency_table

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
        
        newBlock = "BB0"
        for j in range(i):
            if parsed[j]["instrAddress"] == -1:
                newBlock = parsed[j]["opcode"]
                continue
            if (parsed[j]["dest"] == parsed[i]["src1"] or parsed[j]["dest"] == parsed[i]["src2"]) and currentBlock != newBlock and parsed[j]["dest"] != None:
                dependency_table[i]["interloopDep"].append(parsed[j]["instrAddress"])

    
    currentBlock = "BB0"
    