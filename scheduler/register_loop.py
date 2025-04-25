from utils import get_instruction_with_id, get_unit_type, init_bundle, sort_instructions_by_unit


def register_loop(schedule,parsedInstruction, dependencyTable):
    
    schedule = convert_back_to_register(schedule, parsedInstruction)
    schedule = sort_instructions_by_unit(schedule)
    
    
    start_index = 1
    loop_dep={}
    reg_transform = {}
    for idx, bundle in enumerate(schedule):
        for instr in bundle:
            if instr["opcode"] != "st" and instr["dest"] and instr["dest"].startswith("x"):
                new_reg = f"x{start_index}"
                loop_dep.setdefault(new_reg, [])
                if instr["dest"] == instr["src1"]:
                    print(f'Checking instr @ {instr["instrAddress"]}: dest={instr["dest"]}, src1={instr["src1"]}, src2={instr["src2"]}')

                    loop_dep[new_reg].append(instr["src1"])
                if instr["dest"] == instr["src2"]:
                    print(f'Checking instr @ {instr["instrAddress"]}: dest={instr["dest"]}, src1={instr["src1"]}, src2={instr["src2"]}')

                    loop_dep[new_reg].append(instr["src2"])
                if reg_transform.get(instr["dest"])is None:
                    reg_transform[instr["dest"]] = new_reg
                instr["dest"] = new_reg
                
                start_index += 1
    
    for k in schedule:  
        for l in k:
            print("loop_dep", l)
            l["src1"] = reg_transform.get(l["src1"]) if l["src1"] is not None and l["src1"].startswith("x") else l["src1"]
            l["src2"] = reg_transform.get(l["src2"])if l["src2"] is not None and l["src2"].startswith("x") else l["src2"]
            if l["memSrc1"] is not None:
                start = l["memSrc1"].find('(')
                end = l["memSrc1"].find(')')
                if start != -1 and end != -1:
                    reg_in_mem = l["memSrc1"][start+1:end]
                    renamed_reg = reg_transform.get(reg_in_mem)
                    if renamed_reg:
                        l["memSrc1"] = l["memSrc1"].replace(reg_in_mem, renamed_reg)
            # if l["instrAddress"] < instr["instrAddress"]:
            if l["memSrc2"] is not None:
                start = l["memSrc2"].find('(')
                end = l["memSrc2"].find(')')
                if start != -1 and end != -1:
                    reg_in_mem = l["memSrc2"][start+1:end]
                    renamed_reg = reg_transform.get(reg_in_mem)
                    if renamed_reg:
                        l["memSrc2"] = l["memSrc2"].replace(reg_in_mem, renamed_reg)
                            
                # print("found in memSrc1", l["memSrc1"])
                # print("replace", old_reg, instr["dest"])
                        
                # l["memSrc1"] = l["memSrc1"].replace(old_reg, instr["dest"])
        #     if l["instrAddress"] > instr["instrAddress"]:
        #         if l["src1"] == old_reg:
        #             l["src1"] = instr["dest"]
        #         if l["src2"] == old_reg:
        #             l["src2"] = instr["dest"]
        #         if  l["memSrc1"] is not None :
        #             if old_reg in l["memSrc1"]:
        #                 print("found in memSrc1", l["memSrc1"])
        #                 print("replace", old_reg, instr["dest"])
                        
        #                 l["memSrc1"] = l["memSrc1"].replace(old_reg, instr["dest"])
              
    print("Loop-carried deps map:", loop_dep)     
    print(schedule)
    # for idx,i in enumerate(schedule):
    #     toChange = None
    #     for j in i:
    #         if j["opcode"] != "st":
    #             if j["dest"].startswith("x"):
    #                 toChange = j["dest"]
    #                 j["dest"] = "x"+str(start_index)
    #                 start_index += 1
    #         if toChange is None:
    #             continue
    #         for k in schedule[idx+1:]:
    #             for l in k:
    #                 if l["instrAddress"] > j["instrAddress"]:
    #                     if l["src1"] == toChange:
    #                         l["src1"] = j["dest"]
    #                     if l["src2"] == toChange:
    #                         l["src2"] = j["dest"]
    #                     if  l["memSrc1"] is not None :
    #                         if toChange in l["memSrc1"]:
    #                             l["memSrc1"] = l["memSrc1"].replace(toChange, j["dest"])
                            
    # print(schedule)
    # for instr in dependencyTable:
    #     print(instr["instrAddress"], instr["interloopDep"])
    #     for indexDep in instr["interloopDep"]:
    #         print("indexDep", indexDep)
    #         for bundle in schedule:
    #             for instr in bundle:
    #                 if instr["instrAddress"] == indexDep:
    #                     print("foudnf for  ", instr["instrAddress"])
                        
                        
    return schedule

def convert_back_to_register(schedule, parsedInstruction):
    """
    Converts the schedule back to register format.
    """
    new_schedule = []
    for cycle in schedule:
        bundle = []
        for instr in cycle["instrs"]:   
            instr_data = get_instruction_with_id(parsedInstruction, instr)
            if instr_data:
                bundle.append(instr_data)
        new_schedule.append(bundle)
    return new_schedule