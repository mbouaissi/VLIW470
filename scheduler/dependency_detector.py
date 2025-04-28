import re
import copy


from utils import *

def detector(instruction, needToParse = True):
    parsed_instruction = instruction
    if  needToParse:
        parsed_instruction = parse_instruction(instruction)
    dependency_analysis_result = dependency_analysis(parsed_instruction)
    return (parsed_instruction,dependency_analysis_result)

def parse_instruction(instructions):
    decoded = []
    for idx, inst in enumerate(instructions):
        parts = inst.replace(",", "").split()
        opcode, *operands = parts + [None] * (4 - len(parts))
        dest, src1_raw, src2_raw = operands[:3]

        src1_info, src2_info = parse_mem_operand(src1_raw), parse_mem_operand(src2_raw)
        src1 = src1_info["base"] if src1_info else src1_raw
        src2 = src2_info["base"] if src2_info else src2_raw

        decoded.append({
            "instrAddress": idx, "opcode": opcode, "dest": dest,
            "src1": src1, "src2": src2,
            "memSrc1": src1_info["raw"] if src1_info else None,
            "memSrc2": src2_info["raw"] if src2_info else None,
        })

    for idx, instr in enumerate(decoded):
        if instr["opcode"] == "loop":
            decoded.insert(idx + 1, empty_block("BB2"))
            decoded.insert(int(instr["dest"]), empty_block("BB1"))
            break

    decoded.insert(0, empty_block("BB0"))
    return decoded

def dependency_analysis(parsed):
    """
    Perform dependency analysis on the parsed instructions.
    """
    dependency_table = []
    for i in range(len(parsed)):
        dependency_table.append({"instrAddress": parsed[i]["instrAddress"], "localDependency": [], "interloopDep": [], "loopInvarDep" : [],"postLoopDep": []})
    
    
        
    detect_local_dependencies(parsed, dependency_table)
    detect_interloop_dependencies(parsed, dependency_table)
    detect_loop_invariant_dependencies(parsed, dependency_table)
    detect_post_loop_dependencies(parsed, dependency_table)
    
    # Make a deep copy for each version
    latest_timestamp = clean_dependencies_latest_timestamp(copy.deepcopy(dependency_table))
    only_registers   = clean_dependencies_only_registers(copy.deepcopy(dependency_table))
    only_timestamp   = clean_dependencies_only_timestamp(copy.deepcopy(dependency_table))

    return (latest_timestamp, only_registers, only_timestamp)

def detect_local_dependencies(parsed, dependency_table):
    """
    Detect local dependencies within the same block.
    """
    currentBlock = "BB0"
    for i, instr in enumerate(parsed):
        if instr["instrAddress"] == -1:
            currentBlock = instr["opcode"]
            continue
        newBlock = "BB0"
        for j, before_instr in enumerate(parsed[:i]):
            if before_instr["instrAddress"] == -1:
                newBlock = before_instr["opcode"]
                continue
            if newBlock != currentBlock:
                continue
            
            producers = get_producer_register(before_instr)
            consumers = get_consumer_register(instr)
            intersection = producers & consumers
            if (intersection and instr["dest"] ):
                dependency_table[i]["localDependency"].append((before_instr["instrAddress"], before_instr["dest"]))
    
def detect_interloop_dependencies(parsed, dependency_table):
    """
    Detect interloop in different blocks or iteration.
    """
    currentBlock = "BB0"
    for i , instr in enumerate(parsed):
        if instr["instrAddress"] == -1:
            currentBlock = instr["opcode"]
            continue
        if currentBlock != "BB1":
            continue
        newBlock = "BB0"
        toAdd1 = -1
        toAdd2 = -1
        for j, later_instr in enumerate(parsed):
            if later_instr["instrAddress"] == -1:
                newBlock = later_instr["opcode"]
                continue
            
            
            producers = get_producer_register(later_instr)
            consumers = get_consumer_register(instr)

            intersection = producers & consumers
            for reg in intersection:
                if (intersection and later_instr["dest"]):
                    match newBlock:
                        case "BB0":
                                toAdd1 = (later_instr["instrAddress"], reg)
                                continue
                        case "BB1":
                                if (later_instr["instrAddress"]>=instr['instrAddress']):
                                    toAdd2 = (later_instr["instrAddress"],reg)
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
    for i, instr in enumerate(parsed):
        if instr["instrAddress"] == -1:
            currentBlock = instr["opcode"]
            if currentBlock != "BB0":
                break
        newBlock = "BB0"
        toAdd = None
        dest = -1
        for j, later_instr in enumerate(parsed[i + 1:], start=i + 1):
            if later_instr["instrAddress"] == -1:
                newBlock = later_instr["opcode"]
                continue
            if later_instr["dest"] in get_producer_register(instr) :
                toAdd = None
                break
            if (get_producer_register(instr) & get_consumer_register(later_instr)) and currentBlock == "BB0" and newBlock!="BB0" and get_producer_register(instr)!= None:
                toAdd = (j,instr["instrAddress"])
                dest = later_instr["dest"]
        if toAdd != None:
            dependency_table[toAdd[0]]["loopInvarDep"].append((toAdd[1],dest))

            
def detect_post_loop_dependencies(parsed, dep_table):
    """
    Detect post-loop dependencies.
    """
    post_loop = False
    for i, instr_i in enumerate(parsed):
        if instr_i["instrAddress"] == -1:
            post_loop = (instr_i["opcode"] == "BB2")
            continue
        if not post_loop:
            continue
        for j in range(i):
            if parsed[j]["instrAddress"] != -1 and get_producer_register(instr_i) & get_consumer_register(parsed[j]):
                for reg in get_producer_register(instr_i) & get_consumer_register(parsed[j]):
                    dep_table[i]["postLoopDep"].append((parsed[j]["instrAddress"], reg))


def clean_dependencies(dep_table):
    for entry in dep_table:
        for key in ["localDependency", "interloopDep", "loopInvarDep","postLoopDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep just the list of latest instruction addresses
            #entry[key] = list(reg_map.values())

def clean_dependencies_latest_timestamp(dep_table):
    for entry in dep_table:
        for key in ["localDependency",  "loopInvarDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep (timestamp, register) pairs, sorted if needed
            entry[key] = [(addr, reg) for reg, addr in reg_map.items()]
    for entry in dep_table:
        for key in [  "postLoopDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep (timestamp, register) pairs, sorted if needed
            entry[key] = [(addr, reg) for reg, addr in reg_map.items()]
    return dep_table
def clean_dependencies_only_timestamp(dep_table):
    for entry in dep_table:
        for key in ["localDependency", "loopInvarDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep only the timestamps
            entry[key] = list(reg_map.values())
    for entry in dep_table:
        for key in [  "postLoopDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep (timestamp, register) pairs, sorted if needed
            entry[key] = [(addr, reg) for reg, addr in reg_map.items()]
            
    return dep_table
def clean_dependencies_only_registers(dep_table):
    for entry in dep_table:
        for key in ["localDependency", "loopInvarDep"]:
            registers = set()
            for _, reg in entry[key]:
                registers.add(reg)
            entry[key] = list(registers)
    for entry in dep_table:
        for key in [  "postLoopDep"]:
            reg_map = {}  # reg -> latest instr address
            for instr_addr, reg in entry[key]:
                if reg not in reg_map or instr_addr > reg_map[reg]:
                    reg_map[reg] = instr_addr
            # Keep (timestamp, register) pairs, sorted if needed
            entry[key] = [(addr, reg) for reg, addr in reg_map.items()]

    return dep_table

           
def get_consumer_register(instr):
    regs = []

    if instr["opcode"] == "st" and  instr["dest"] and instr["dest"].startswith("x"): 
        regs.append(instr["dest"])
    
    if instr["src1"] and instr["src1"].startswith("x"): 
        regs.append(instr["src1"])
    if instr["src2"] and instr["src2"].startswith("x"): 
        regs.append(instr["src2"])
    
    return set(regs)

def get_producer_register(instr):
    regs = []
    if instr["opcode"] == "st":
        return set()
    if instr["dest"] and instr["dest"].startswith("x") : 
        regs.append(instr["dest"])
    # if instr["opcode"] == "st":
    #     # For store, both dest and src important
    #     if instr["src1"] and instr["src1"].startswith("x"): 
    #         regs.append(instr["src1"])
    #     if instr["src2"] and instr["src2"].startswith("x"): 
    #         regs.append(instr["src2"])
    
    return set(regs)
