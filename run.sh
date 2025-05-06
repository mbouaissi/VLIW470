#!/bin/bash

INPUT=$1
OUTPUT_SIMPLE=$2
OUTPUT_PIP=$3

echo "Running simulator: $INPUT → $OUTPUT"
python3 scheduler/main.py "$INPUT" "$OUTPUT_SIMPLE"  "$OUTPUT_PIP"

