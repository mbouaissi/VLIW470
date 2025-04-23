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
            decoded_instructions.insert(idx+1,{
                "instrAddress": -1,
                "opcode": "BB2",
                "dest": None,
                "src1": None,
                "src2": None,
                "memSrc1": None,
                "memSrc2": None,
            })
            whereToInsert = x["dest"]
            decoded_instructions.insert(int(whereToInsert),{
                "instrAddress": -1,
                "opcode": "BB1",
                "dest": None,
                "src1": None,
                "src2": None,
                "memSrc1": None,
                "memSrc2": None,
            })
            break
    
    decoded_instructions.insert(0,{
        "instrAddress": -1,
        "opcode": "BB0",
        "dest": None,
        "src1": None,
        "src2": None,
        "memSrc1":None,
        "memSrc2": None,
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
    detect_interloop_dependencies(parsed, dependency_table)
    detect_loop_invariant_dependencies(parsed, dependency_table)
    detect_post_loop_dependencies(parsed, dependency_table)
    
    clean_dependencies(dependency_table)
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
            if (parsed[j]["dest"] in get_consumer_register(parsed[i]) and parsed[j]["dest"] is not None) and currentBlock == newBlock and parsed[j]["dest"] != None:
                dependency_table[i]["localDependency"].append((parsed[j]["instrAddress"], parsed[j]["dest"]))
                
def detect_interloop_dependencies(parsed, dependency_table):
    """
    Detect interloop in different blocks or iteration.
    """
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
        dest = -1
        for j in range(len(parsed)):
            dest = parsed[j]["dest"]
            if parsed[j]["instrAddress"] == -1:
                newBlock = parsed[j]["opcode"]
                continue
            if (parsed[j]["dest"] in get_consumer_register(parsed[i]) and parsed[j]["dest"] is not None):
                match newBlock:
                    case "BB0":
                            toAdd1 = parsed[j]["instrAddress"]
                            continue
                    case "BB1":
                            if (parsed[j]["instrAddress"]>=parsed[i]['instrAddress']):
                                toAdd2 = parsed[j]["instrAddress"]
                            continue
                    case "BB2":
                        break
        if toAdd2 != -1:
            dependency_table[i]["interloopDep"].append(toAdd2)
            if toAdd1 != -1:
                dependency_table[i]["interloopDep"].append(toAdd1)

def detect_loop_invariant_dependencies(parsed, dependency_table):
    """
    Detect loop invariant dependencies.
    """
    currentBlock = "BB0"
    for i in range(len(parsed)):
        if parsed[i]["instrAddress"] == -1:
            currentBlock = parsed[i]["opcode"]
            if currentBlock != "BB0":
                break
        newBlock = "BB0"
        toAdd = None
        dest = -1
        for j in range(i+1,len(parsed)):
            if parsed[j]["instrAddress"] == -1:
                newBlock = parsed[j]["opcode"]
                continue
            if parsed[j]["dest"] in get_producer_register(parsed[i]) :
                toAdd = None
                break
            if (get_producer_register(parsed[i]) & get_consumer_register(parsed[j])) and currentBlock == "BB0" and newBlock!="BB0" and get_producer_register(parsed[i])!= None:
                toAdd = (j,parsed[i]["instrAddress"])
                dest = parsed[j]["dest"]
        if toAdd != None:
            dependency_table[toAdd[0]]["loopInvarDep"].append((toAdd[1],dest))
            
def detect_post_loop_dependencies(parsed, dependency_table):
    """
    Detect loop invariant dependencies.
    """
    currentBlock = "BB0"
    indexBB1 = -1
    indexBB2 = -1
    for i in range(len(parsed)):
        if parsed[i]["instrAddress"] == -1:
            currentBlock = parsed[i]["opcode"]
            if currentBlock == "BB2":
                indexBB2 = i
        if currentBlock != "BB2":
            continue
        for j in range(indexBB2):
            if (get_producer_register(parsed[i]) &  get_consumer_register(parsed[j])) and get_producer_register(parsed[i])!= None:
                element = get_producer_register(parsed[i]) &  get_consumer_register(parsed[j])
                for x in element:
                    dependency_table[i]["postLoopDep"].append((parsed[j]["instrAddress"],x) )

def clean_dependencies(dep_table):
    for entry in dep_table:
        for key in ["localDependency",  "loopInvarDep","postLoopDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep just the list of latest instruction addresses
            entry[key] = list(reg_map.values())


def get_consumer_register(instr):
    regs = []

    if instr["src1"] and instr["src1"].startswith("x"): 
        regs.append(instr["src1"])
    if instr["src2"] and instr["src2"].startswith("x"): 
        regs.append(instr["src2"])
    
    return set(regs)

def get_producer_register(instr):
    regs = []
    if instr["dest"] and instr["dest"].startswith("x"): 
        regs.append(instr["dest"])
    if instr["opcode"] == "st":
        # For store, both dest and src important
        if instr["src1"] and instr["src1"].startswith("x"): 
            regs.append(instr["src1"])
        if instr["src2"] and instr["src2"].startswith("x"): 
            regs.append(instr["src2"])
    
    return set(regs)