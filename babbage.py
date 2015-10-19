#!/usr/bin/env python
import re
import sys
import string
import random

STORE_MAX = 999

def log(*args):
    print("[LOG] ", *args, file=sys.stderr)

class Card(object):
    pass

################
# OPERATION CARDS
################
class ArithmeticOpCard(Card):
    def __init__(self, operation):
        valid_operations = set(["+", "-", "*", "/"])
        assert(operation in valid_operations)
        self.operation = operation

    def __str__(self):
        return self.operation

class PCard(Card):
    def __str__(self):
        return "P"

################
# NUMERIC CARDS
################
class NumericCard(Card):
    def __init__(self, store_loc, value):
        self.store_loc = store_loc
        self.value = value

class NCard(NumericCard):
    def __str__(self):
        return "N{0} {1}".format(str(self.store_loc), str(self.value))

################
# VARIABLE CARDS
################
class VariableCard(Card):
    def __init__(self, store_loc, is_prime=False):
        self.store_loc = store_loc
        self.is_prime  = is_prime

class LCard(VariableCard):
    def __str__(self):
        return "L{}".format(str(self.store_loc))

class ZCard(VariableCard):
    def __str__(self):
        return "Z{}".format(str(self.store_loc))

class SCard(VariableCard):
    def __str__(self):
        return "S{0}{1}".format(str(self.store_loc), "'" if self.is_prime else "")

store = []
for i in range(0, STORE_MAX+1):
    store.append(0)

varname_to_store_loc = {}
used_store_locs = set()

def malloc(varname):
    for i in range(0, STORE_MAX+1):
        if i not in used_store_locs:
            used_store_locs.add(i)
            varname_to_store_loc[varname] = i
            store[i] = 0
            return i

def free(varname):
    assert(does_var_exist(varname))
    store_loc = varname_to_store_loc[varname]
    used_store_locs.remove(store_loc)
    varname_to_store_loc.pop(varname, None)

def set_val(varname, val):
    assert(varname in varname_to_store_loc)
    loc = varname_to_store_loc[varname]
    store[loc] = val

def does_var_exist(varname):
    return varname in varname_to_store_loc

def get_tmp_varname():
    while True:
        rand_string = "tmp" + "".join(random.choice(string.ascii_lowercase) for _ in range(5))
        if not does_var_exist(rand_string):
            return rand_string

def compile(source):
    """ Returns a list of Cards """
    cards = []

    for line in source.splitlines():
        log("Parsing line: " + line)

        # Variable assignment
        match = re.match("([a-z]+)\s*=\s*(\d+)", line)
        if match:
            varname = match.group(1)
            val = int(match.group(2))
            log("Detected variable assignment. varname: {0}, val: {1}".format(varname, str(val)))
            loc = malloc(varname)
            set_val(varname, val)
            cards.append(NCard(loc, val))
            continue

        # Assignment from arithmetic computation
        match = re.match("([a-z]+)\s*=\s*(-?\w+)\s*([+-/*])\s*(-?\w+)", line)
        if match:
            dest_var  = match.group(1)
            operand1  = match.group(2)
            operation = match.group(3)
            operand2  = match.group(4)

            # LHS
            # If dest_var does not exist then create it
            if not does_var_exist(dest_var):
                log("dest_var does not exist. Creating it.")
                dest_loc = malloc(dest_var)
            else:
                dest_loc = varname_to_store_loc(dest_var)

            # RHS
            if operand1.isdigit(): # malloc a literal int
                log("op1 is a literal")
                op1_is_literal = True
                n = int(operand1)
                operand1 = get_tmp_varname()
                malloc(operand1)
                set_val(operand1, n)

                # Add the cards
                cards.append(NCard(loc2, n))
            else:
                log("op1 is a variable")
                op1_is_literal = False
                try:
                    assert(does_var_exist(operand1))
                except AssertionError:
                    log("{} hasn't been assigned yet.".format(operand1))
                    sys.exit(1)

            if operand2.isdigit(): # malloc a literal int
                log("op2 is a literal")
                op2_is_literal = True
                n = int(operand2)
                operand2 = get_tmp_varname()
                loc2 = malloc(operand2)
                set_val(operand2, n)

                # Add the cards
                cards.append(NCard(loc2, n))
            else:
                log("op2 is a variable")
                op2_is_literal = False
                try:
                    assert(does_var_exist(operand2))
                except AssertionError:
                    log("{} hasn't been assigned yet.".format(operand2))
                    sys.exit(1)

            loc1 = varname_to_store_loc[operand1]
            loc2 = varname_to_store_loc[operand2]

            log("Parsed arithmetic operation. dest_var: {0}, op1: {1}, operation: {2}, op2: {3}. dest_loc: {4}, loc1: {5}, loc2: {6}".format(varname, operand1, operation, operand2, str(dest_loc), str(loc1), str(loc2)))
            cards.append(ArithmeticOpCard(operation))
            cards.append(LCard(loc1))
            cards.append(LCard(loc2))

            if operation == '/': # for division operations we want the quotient stored
                cards.append(SCard(dest_loc, True))
            else:
                cards.append(SCard(dest_loc, False))

            # If any literals were assigned then free them
            if op1_is_literal:
                free(operand1)

            if op2_is_literal:
                free(operand2)

            continue

        match = re.match("print\s*([a-z]+)", line)
        if match:
            varname = match.group(1)
            log("Parsed print statement for variable: {}".format(varname))

            loc = varname_to_store_loc[varname]

            tmpvar = get_tmp_varname()
            tmploc = malloc(tmpvar) # find an empty storage location

            # Add 0 to the value of the variable so that it's value gets on to the
            # egress axis.
            # First we need to store a 0...
            cards.append(NCard(tmploc, 0))
            cards.append(ArithmeticOpCard("+"))
            cards.append(LCard(tmploc))
            cards.append(LCard(loc))
            cards.append(PCard())

            free(tmpvar)
            continue

    return cards

if __name__ == "__main__":
    source = ""

    if len(sys.argv) > 1:
        source_file = sys.argv[1]
        with open(source_file, "r") as f:
            source = f.read()
    else: 
        source = sys.stdin.read()

    cards = compile(source)
    for card in cards:
        print(card)
