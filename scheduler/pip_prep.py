import re
from utils import *

def pip_prep(instructions, schedule, II, non_modulo, modulo_schedule):
    print("==Pre prep instr==")
    print_schedule(instructions)
    clean_instructions(instructions)
    print("==Post clean==")
    print_schedule(instructions)
    json_schedule = form_json(instructions, schedule)
    json_schedule = loop_prep(json_schedule)
    json_schedule = insert_movs(json_schedule, II, modulo_schedule)
    json_schedule = adjust_loop_address(json_schedule, II)
    json_schedule = generate_predicates(json_schedule, non_modulo)

    return json_schedule

def clean_instructions(instructions):
    def resolve_register_offset(reg_str):
        match = re.match(r"x(\d+)\(\+(\d+),\+(\d+)\)", reg_str)
        if not match:
            return reg_str
        base = int(match.group(1))
        iter_offset = int(match.group(2))
        stage_offset = int(match.group(3))
        total = base + iter_offset + stage_offset
        return f"x{total}"

    def convert_immediate(val):
        if isinstance(val, str) and val.startswith("0x"):
            try:
                return str(int(val, 16))
            except ValueError:
                return val
        return val

    def resolve_fields(instr):
        for field in ['dest', 'src1', 'src2']:
            val = instr.get(field)
            if val:
                # Convert immediates
                val = convert_immediate(val)
                # Clean register offset
                resolved = resolve_register_offset(val)
                instr[field] = resolved

        for mem_field in ['memSrc1', 'memSrc2']:
            val = instr.get(mem_field)
            if not val:
                continue
            match = re.search(r"\((x\d+\(\+\d+,\+\d+\))\)", val)
            if match:
                reg = match.group(1)
                resolved = resolve_register_offset(reg)
                updated = val.replace(reg, resolved)
                instr[mem_field] = updated

    for instr in instructions:
        resolve_fields(instr)


def form_json(instructions, schedule):
    """
    Convertit les bundles du schedule en lignes formatées proprement.
    Slots : [ALU0, ALU1, MULT, MEM, BRANCH]
    """
    instr_map = {instr["instrAddress"]: instr for instr in instructions if instr["instrAddress"] != -1}
    json_schedule = []

    def format_instr(instr):
        if not instr:
            return " nop"

        opcode = instr["opcode"]
        dest = instr.get("dest", "")
        src1 = instr.get("src1", "")
        src2 = instr.get("src2", "")
        mem1 = instr.get("memSrc1", "")
        pred = instr.get("predicate", None)

        prefix = f"({pred}) " if pred else ""

        if opcode == "ld":
            return f"{prefix}{opcode} {dest}, {mem1}"
        elif opcode == "st":
            return f"{prefix}{opcode} {dest}, {mem1}"
        elif opcode in ["add", "sub", "mulu", "addi"]:
            return f"{prefix}{opcode} {dest}, {src1}, {src2}"
        elif opcode == "mov":
            return f"{prefix}{opcode} {dest}, {src1}"
        elif opcode == "loop":
            return f"{prefix}loop.pip {dest}"
        else:
            return f"{prefix}{opcode} {dest}, {src1}, {src2}"

    for bundle in schedule:
        slots = [" nop"] * 5

        instrs = [instr_map.get(i) for i in bundle["instructions"] if i in instr_map]

        # Classify
        alus = [i for i in instrs if i["opcode"] in ["mov", "add", "sub", "addi"]]
        mults = [i for i in instrs if i["opcode"] in ["mulu"]]
        mems = [i for i in instrs if i["opcode"] in ["ld", "st"]]
        branch = [i for i in instrs if i["opcode"] == "loop"]

        # Fill slots
        if len(alus) > 0:
            slots[0] = format_instr(alus[0])
        if len(alus) > 1:
            slots[1] = format_instr(alus[1])
        if len(mults) > 0:
            slots[2] = format_instr(mults[0])
        if len(mems) > 0:
            slots[3] = format_instr(mems[0])
        if len(branch) > 0:
            slots[4] = format_instr(branch[0])

        json_schedule.append(slots)

    return json_schedule


def loop_prep(schedule):
    """
    Returns the schedule with only one iteration of the loop body,
    keeping prologue and epilogue, and skipping repeated loop iterations.
    """
    cleaned = []
    first_loop_idx = None
    second_loop_idx = None

    # Find indices of all 'loop.pip' bundles
    for i, bundle in enumerate(schedule):
        if any("loop.pip" in instr for instr in bundle):
            if first_loop_idx is None:
                first_loop_idx = i
            elif second_loop_idx is None:
                second_loop_idx = i
                break  # We only need the first two

    for i, bundle in enumerate(schedule):
        if second_loop_idx is not None and first_loop_idx < i < second_loop_idx:
            continue  # Skip second iteration of loop body
        if second_loop_idx is not None and i == second_loop_idx:
            continue  # Skip repeated loop.pip
        cleaned.append(bundle)

    return cleaned



def insert_movs(schedule, II, modulo_schedule):
    ec_val = count_stages(modulo_schedule) - 1
    target_instrs = [f"mov EC, {ec_val}", "mov p32, true"]
    loop_idx = next((i for i, row in enumerate(schedule) if any("loop.pip" in instr for instr in row)), None)

    target_idx = loop_idx - II + 1 
    row = schedule[target_idx]

    # Vérifie si les deux premiers slots sont des 'nop'
    if row[0].strip() == "nop" and row[1].strip() == "nop":
        row[0] = target_instrs[0]
        row[1] = target_instrs[1]
    else:
        # Insérer une nouvelle ligne avant
        new_row = [target_instrs[0], target_instrs[1], "nop", "nop", "nop"]
        schedule.insert(target_idx, new_row)

    return schedule



def adjust_loop_address(schedule, II):
    for i, row in enumerate(schedule):
        for j, instr in enumerate(row):
            instr = instr.strip()
            if instr.startswith("loop.pip"):
                # Correct loop pip target to i - II + 1
                correct_target = i - II + 1 
                row[j] = f"loop.pip {correct_target}"
    return schedule


def generate_predicates(schedule, non_modulo):
    # Trouver l’index du loop.pip
    loop_idx = next((i for i, row in enumerate(schedule) if any("loop.pip" in instr for instr in row)), None)
    if loop_idx is None:
        raise ValueError("No 'loop.pip' found in schedule.")

    # Obtenir l’indice de départ de boucle
    loop_instr = next(instr for instr in schedule[loop_idx] if "loop.pip" in instr)
    try:
        loop_start = int(loop_instr.strip().split()[1])
    except:
        raise ValueError("Malformed loop.pip")

    # Appliquer p32/p33 dans le corps de boucle selon les bundles non-modulo
    for i in range(loop_start, loop_idx + 1):
        row = schedule[i]
        b = non_modulo[i - loop_start]  # bundle correspondant

        used = {"ALU": 0, "MULT": 0, "MEM": 0}  # BRANCH ignoré totalement

        for j in range(len(row)):
            instr = row[j].strip()
            if instr == "nop" or instr.startswith("(p32)") or instr.startswith("(p33)"):
                continue

            # Déterminer type d’unité selon colonne
            if j in [0, 1]:
                unit = "ALU"
            elif j == 2:
                unit = "MULT"
            elif j == 3:
                unit = "MEM"
            elif j == 4:
                # BRANCH → laisser inchangé
                continue
            else:
                continue  # sécurité

            # Décider du prédicat
            if used[unit] < b[unit]:
                pred = "p32"
            else:
                pred = "p33"

            used[unit] += 1
            row[j] = f"({pred}) {instr}"

    return schedule