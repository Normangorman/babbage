#!/bin/bash
# Compile a .bab file and then run it with aes
mkdir -p bin

base=$(basename $1)
compiled_file="bin/${base%.bab}.eng"
./babbage.py $1 > $compiled_file
java -cp engine aes $compiled_file
