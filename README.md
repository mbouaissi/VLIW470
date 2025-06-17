# VLIW470 Instruction Scheduler

This project implements a **cycle-accurate static instruction scheduler** for a simplified **VLIW (Very Long Instruction Word)** processor named **VLIW470**, featuring a subset of the **RISC-V** instruction set and enhanced with **Itanium-style loop support**.

Developed as part of the **CS-470: Advanced Computer Architecture** course at **EPFL**, taught by **Prof. Paolo Ienne**.

---

## Project Overview

The scheduler statically transforms a sequential RISC-V program into two parallel VLIW schedules:
- A **baseline VLIW schedule** using `loop` instructions
- An **optimized pipelined schedule** using `loop.pip`, software pipelining, predicate registers, and rotating registers

---

## Key Features

- **Bundle-based VLIW scheduling** with ALU, Mult, Mem, and Branch slots  
- **ASAP (As Soon As Possible) scheduling** algorithm  
- **Software pipelining** with initiation interval analysis and modulo scheduling  
- **Rotating register support** using RRB (Register Rotation Base)  
- **Dependency analysis** (RAW, interloop, loop invariants, etc.)  
- **Predicate-controlled execution** via predicate registers `p0–p95`  
- Support for **loop draining and epilogue scheduling**

---

## Repository Structure

- `scheduler/` — Core logic of instruction analysis, scheduling, and register allocation
- `build.sh` — Build script (empty for Python or includes compilation steps)
- `run.sh` — Run script:  
  ```bash
  ./run.sh input.json loop.json looppip.json
  ```
- `test/` — JSON-based input and reference output test cases
- `report.pdf` — Full technical report (if provided)
- `README.md` — This file

---

## Input / Output Format

- **Input**: A sequential RISC-V assembly program in JSON (add, mulu, ld, st, etc.)
- **Output**:
  - `loop.json`: schedule using `loop` instruction
  - `looppip.json`: optimized schedule using `loop.pip`, predicate execution, rotating registers

Example:
```json
[
  "mov LC, 100",
  "mov x2, 0x1000",
  ...
  "loop 4",
  "st x3, 0(x2)"
]
```

---

## Grading Environment

The project is compatible with the CS470 Docker grading environment:
```bash
sudo docker build . -t cs470
sudo docker run -it -v $(pwd):/home/root/cs470 cs470
```

Then inside the container:
```bash
cd /home/root/cs470
./runall.sh
./testall.sh
```

---

## Authors

Menzo Bouaïssi & Thomas Lenges


