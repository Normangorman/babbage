#!/usr/bin/env python3
import re
import sys
import string
import random

STORE_MAX = 999
KEYWORDS = set(["print", "halt", "and", "or", "while", "end"])

def log(*args):
    print("[LOG] ", *args, file=sys.stderr)

class Card(object):
    pass

class CommentCard(Card):
    def __init__(self, comment):
        self.comment = comment

    def __str__(self):
        return ". " + self.comment

class HaltCard(Card):
    def __str__(self):
        return "H"

class BellCard(Card):
    def __str__(self):
        return "B"

class ArithmeticOpCard(Card):
    def __init__(self, operation):
        valid_operations = set(["+", "-", "*", "/"])
        assert(operation in valid_operations)
        self.operation = operation

    def __str__(self):
        return self.operation

class PrintCard(Card):
    def __str__(self):
        return "P"

class CondCard(Card):
    def __init__(self, direction, depends_on_lever, num_lines):
        assert(direction == "F" or direction == "B")
        self.direction = direction
        self.depends_on_lever = depends_on_lever
        self.num_lines = num_lines

    def __str__(self):
        lever_letter = "?" if self.depends_on_lever else "+"
        return "C{0}{1}{2}".format(self.direction, lever_letter, str(self.num_lines))

class NumCard(Card):
    def __init__(self, store_loc, value):
        self.store_loc = store_loc
        self.value = value

    def __str__(self):
        return "N{0} {1}".format(str(self.store_loc), str(self.value))

class LoadCard(Card):
    def __init__(self, store_loc):
        self.store_loc = store_loc

    def __str__(self):
        return "L{}".format(str(self.store_loc))

class ZeroCard(Card):
    def __init__(self, store_loc):
        self.store_loc = store_loc

    def __str__(self):
        return "Z{}".format(str(self.store_loc))

class StoreCard(Card):
    def __init__(self, store_loc, is_prime=False):
        self.store_loc = store_loc
        self.is_prime = is_prime

    def __str__(self):
        return "S{0}{1}".format(str(self.store_loc), "'" if self.is_prime else "")

varname_to_store_loc = {}
used_store_locs = set()

def malloc(varname):
    assert(varname not in KEYWORDS)
    for i in range(0, STORE_MAX+1):
        if i not in used_store_locs:
            used_store_locs.add(i)
            varname_to_store_loc[varname] = i
            return i

def free(varname):
    assert(does_var_exist(varname))
    store_loc = varname_to_store_loc[varname]
    used_store_locs.remove(store_loc)
    varname_to_store_loc.pop(varname, None)

def does_var_exist(varname):
    return varname in varname_to_store_loc

def get_tmp_varname():
    while True:
        rand_string = "tmp" + "".join(random.choice(string.ascii_lowercase) for _ in range(5))
        if not does_var_exist(rand_string):
            return rand_string

def is_integer(string):
    try:
        int(string)
        return True
    except ValueError:
        return False

def compile_unary_op(operation, in_loc, out_loc):
    cards = []

    if operation == "!":
        cards.append(CommentCard("Begin !loc{0} -> loc{1}".format(str(in_loc), str(out_loc))))

        # Divide the input by itself. If division by 0, save 1 to out_loc
        cards.append(ArithmeticOpCard("/"))
        cards.append(LoadCard(in_loc))
        cards.append(LoadCard(in_loc))
        cards.append(CondCard("F", True, 1))
        cards.append(CondCard("F", False, 2))
        cards.append(NumCard(out_loc, 1))
        cards.append(CondCard("F", False, 1))
        cards.append(NumCard(out_loc, 0))

        return cards

def compile_bin_op(operation, in1, in2, out):
    cards = []
    basic_operations = set(["+", "-", "*"])
    if operation in basic_operations:
        cards.append(CommentCard("Begin loc{0} + loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))
        cards.append(ArithmeticOpCard(operation))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))
        cards.append(StoreCard(out))
    elif operation == "/":
        cards.append(CommentCard("Begin loc{0} / loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))
        cards.append(ArithmeticOpCard("/"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))
        cards.append(StoreCard(out, True)) # quotient is the placed on prime egress
    elif operation == "%":
        cards.append(CommentCard("Begin loc{0} % loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))
        cards.append(ArithmeticOpCard("/"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))
        cards.append(StoreCard(out, False)) # remainder is the placed on non-prime egress
    elif operation == "==":
        cards.append(CommentCard("Begin loc{0} == loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))
        # Compute the difference between the operands
        cards.append(ArithmeticOpCard("-"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))

        difference_varname = get_tmp_varname()
        diff_loc = malloc(difference_varname)
        cards.append(StoreCard(diff_loc))

        # Reuse loc1 as the first operand for division because we just need an arbitrary value.
        # if the difference is 0, division by 0 will occur and the lever will be triggered.
        # thus we know if two numbers are equal.
        cards.append(ArithmeticOpCard("/"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(diff_loc))

        # If the lever is set, the numbers are equal so set output to 1.
        # Else set it to 0.
        # CF?1
        # CF+2
        # N{dest_loc} 1
        # CF+1
        # N{dest_loc} 0
        # ...
        cards.append(CondCard("F", True, 1))
        cards.append(CondCard("F", False, 2))
        cards.append(NumCard(out, 1))
        cards.append(CondCard("F", False, 1))
        cards.append(NumCard(out, 0))

        free(difference_varname)
    elif operation == ">": # CURRENTLY BROKEN FOR EQUAL OPERANDS OR SECOND OPERAND BEING 0
        cards.append(CommentCard("Begin loc{0} > loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))

        # Compute the difference between the operands
        cards.append(ArithmeticOpCard("-"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))

        # If the lever is set, the sign is different so in1 < in2, so output is 0
        # Else set it to 0.
        # CF?1
        # CF+2
        # N{dest_loc} 0
        # CF+1
        # N{dest_loc} 1
        # ...
        cards.append(CondCard("F", True, 1))
        cards.append(CondCard("F", False, 2))
        cards.append(NumCard(out, 0))
        cards.append(CondCard("F", False, 1))
        cards.append(NumCard(out, 1))
    elif operation == "<": 
        return compile_bin_op(">", in2, in1, out) # just reverse the operands
    elif operation == "or":
        # Compute !((x + y) == 0)
        cards.append(CommentCard("Begin loc{0} || loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))

        addition_var = get_tmp_varname()
        addition_loc = malloc(addition_var)
        cards.append(ArithmeticOpCard("+"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))
        cards.append(StoreCard(addition_loc))

        zero_var = get_tmp_varname()
        zero_loc = malloc(zero_var)
        cards.append(NumCard(zero_loc, 0))

        equality_var = get_tmp_varname()
        equality_loc = malloc(equality_var)
        for card in compile_bin_op("==", addition_loc, zero_loc, equality_loc):
            cards.append(card)

        # Negate the equality with 0 to get the output
        for card in compile_unary_op("!", equality_loc, out):
            cards.append(card)

        free(addition_var)
        free(zero_var)
        free(equality_var)
        return cards
    elif operation == "and":
        # Multiply the operands together and check if the result is greater than 0
        cards.append(CommentCard("Begin loc{0} && loc{1} -> loc{2}".format(str(in1), str(in2), str(out))))

        mult_var = get_tmp_varname()
        mult_loc = malloc(mult_var)

        cards.append(ArithmeticOpCard("*"))
        cards.append(LoadCard(in1))
        cards.append(LoadCard(in2))
        cards.append(StoreCard(mult_loc))

        one_var = get_tmp_varname()
        one_loc = malloc(one_var)
        cards.append(NumCard(one_loc, 1))

        for card in compile_bin_op("==", mult_loc, one_loc, out):
            cards.append(card)

        free(mult_var)
        free(one_var)
        return cards

    return cards

def compile_expr(expr, out_loc):
    """ Compiles the expression in a way that saves the result to out_loc """
    expr = expr.strip()
    cards = []

    cards.append(CommentCard("Begin expr \"{0}\" -> loc{1}".format(expr, str(out_loc))))

    # Parse literal integer
    if is_integer(expr):
        log("compile_expr: parsed integer literal " + expr)
        cards.append(NumCard(out_loc, int(expr)))
        return cards

    # Parse variable name
    match = re.match("[a-z]+$", expr)
    if match:
        log("compile_expr: parsed varname " + expr)
        varname = match.group(0)

        if not does_var_exist(varname):
            log("Variable does not exist!")
            sys.exit(1)

        var_loc = varname_to_store_loc[varname]

        # Since we have no mov instruction, perform the computation x + 0 and store this in out_loc
        tmp_var = get_tmp_varname()
        tmp_loc = malloc(tmp_var)

        cards.append(NumCard(tmp_loc, 0))
        cards.append(ArithmeticOpCard("+"))
        cards.append(LoadCard(var_loc))
        cards.append(LoadCard(tmp_loc))
        cards.append(StoreCard(out_loc))

        free(tmp_var)
        return cards

    # Parse unary operation
    if expr[0] == '!':
        subexpr = expr[1:]

        subexpr_var = get_tmp_varname()
        subexpr_loc = malloc(subexpr_var)
        for card in compile_expr(subexpr, subexpr_loc):
            cards.append(card)

        for card in compile_unary_op("!", subexpr_loc, out_loc):
            cards.append(card)

        free(subexpr_var)
        return cards

    # Parse binary operation
    if expr[0] == '(' and expr[-1] == ')':
        expr = expr[1:-1]

        left_operand  = ""
        operation     = ""
        right_operand = ""

        cursor = 0
        def parse_unit():
            nonlocal cursor
            log("parse_unit called. cursor: " + str(cursor)) 
            cursor_start = cursor
            cursor_end   = cursor
            operand      = ""

            if expr[cursor_start] != '(': # it's a variable name, literal or operation
                while cursor_end < len(expr) and expr[cursor_end] != ' ': 
                    log("cursor_end: {0}, char {1}".format(str(cursor), expr[cursor_end]))
                    cursor_end += 1
            else:
                bracket_level = 1
                cursor_end += 1
                while bracket_level > 0:
                    if expr[cursor_end] == '(':
                        bracket_level += 1
                    elif expr[cursor_end] == ')':
                        bracket_level -= 1
                    cursor_end += 1

            cursor = cursor_end
            return expr[cursor_start : cursor_end]

        # strip spaces
        while expr[cursor] == ' ': cursor += 1
        left_operand = parse_unit()

        while expr[cursor] == ' ': cursor += 1
        operation = parse_unit()

        while expr[cursor] == ' ': cursor += 1
        right_operand = parse_unit()

        log("left_operand: {0}, operation: {1}, right_operand: {2}".format(left_operand, operation, right_operand))

        # Evaluate each operand recursively
        left_op_name = get_tmp_varname()
        left_op_loc  = malloc(left_op_name)
        for card in compile_expr(left_operand, left_op_loc):
            cards.append(card)

        right_op_name = get_tmp_varname()
        right_op_loc  = malloc(right_op_name)
        for card in compile_expr(right_operand, right_op_loc):
            cards.append(card)

        # Once fully evaluated, perform the operation
        for card in compile_bin_op(operation, left_op_loc, right_op_loc, out_loc):
            cards.append(card)

        free(left_op_name)
        free(right_op_name)

        return cards

    log("Invalid expression: " + expr)
    sys.exit(1)

parser_block_depth = 0
def compile(source, init_line_num=0):
    """ Returns a list of Cards """
    global parser_block_depth
    line_num = init_line_num
    lines = source.splitlines()
    cards = []

    while line_num < len(lines):
        line = lines[line_num].strip()
        line_num += 1

        if len(line) == 0:
            continue

        log("Parsing line: " + line)

        if line[0] == '#': # it's a comment
            continue

        # halt or bell
        match = re.match("halt|bell", line)
        if match:
            command = match.group(0)
            if command == "halt":
                cards.append(HaltCard())
            else:
                cards.append(BellCard())

            continue

        # Variable assignment
        match = re.match("([a-z]+)\s*=\s*(.+)", line)
        if match:
            dest_var = match.group(1)

            if does_var_exist(dest_var):
                dest_loc = varname_to_store_loc[dest_var]
            else:
                dest_loc = malloc(dest_var)

            expr = match.group(2)
            log("Detected variable assignment. dest_var: {0}, expr: {1}".format(dest_var, expr))

            cards.append(CommentCard("Begin variable assignment {0} (loc{1}) = {2}".format(dest_var, str(dest_loc), expr)))
            for card in compile_expr(expr, dest_loc):
                cards.append(card)
            continue

        match = re.match("print\s+(.+)", line)
        if match:
            expr = match.group(1)
            log("Parsed print statement for expr: {}".format(expr))

            cards.append(CommentCard("Begin print statement for \"{0}\"".format(expr)))

            # Store the result of the expression in a temporary variable
            expr_var = get_tmp_varname()
            expr_loc = malloc(expr_var)
            for card in compile_expr(expr, expr_loc):
                cards.append(card)

            tmp_zero_var = get_tmp_varname()
            tmp_zero_loc = malloc(tmp_zero_var)

            # Now add the print card...
            # But first add 0 to the value of the epression so that it's value gets on to the
            # egress axis.
            cards.append(NumCard(tmp_zero_loc, 0))
            cards.append(ArithmeticOpCard("+"))
            cards.append(LoadCard(expr_loc))
            cards.append(LoadCard(tmp_zero_loc))
            cards.append(PrintCard())

            free(expr_var)
            free(tmp_zero_var)
            continue

        match = re.match("while\s+(.+)", line)
        if match:
            expr = match.group(1)
            log("Parsed start of while loop for expr: {0}".format(expr))
            cards.append(CommentCard("Begin while loop for \"{0}\"".format(expr)))

            expr_var = get_tmp_varname()
            expr_loc = malloc(expr_var)
            expr_num_cards = 0
            for card in compile_expr(expr, expr_loc):
                expr_num_cards += 1
                cards.append(card)

            log("Calling compile recursively with line_num: {0}".format(line_num))
            parser_block_depth += 1
            block, block_lines_read = compile(source, line_num) # since line_num is incremented after the current line is read, line_num now refers to the NEXT line to read
            line_num += block_lines_read

            # Get a free memory location and load an arbitrary value into it
            tmp_var = get_tmp_varname()
            tmp_loc = malloc(tmp_var)
            
            cards.append(NumCard(tmp_loc, 1)) # 1 is the arbitrary value.

            cards.append(ArithmeticOpCard("/"))
            cards.append(LoadCard(tmp_loc))
            cards.append(LoadCard(expr_loc))
            cards.append(CondCard("F", True, len(block) + 1))
            for block_line in block:
                cards.append(block_line)
            cards.append(CondCard("B", False, len(block) + expr_num_cards + 6))

            free(expr_var)
            free(tmp_var)
            continue

        # If block
        match = re.match("if\s+(.+)", line)
        if match:
            expr = match.group(1)
            log("Parsed start of if block for expr: {0}".format(expr))
            cards.append(CommentCard("Begin if block for \"{0}\"".format(expr)))
            expr_var = get_tmp_varname()
            expr_loc = malloc(expr_var)
            for card in compile_expr(expr, expr_loc):
                cards.append(card)

            log("Calling compile recursively with line_num: {0}".format(line_num))
            parser_block_depth += 1
            block, block_lines_read = compile(source, line_num)
            line_num += block_lines_read

            # Get a free memory location and load an arbitrary value into it
            tmp_var = get_tmp_varname()
            tmp_loc = malloc(tmp_var)
            cards.append(NumCard(tmp_loc, 1)) # 1 is the arbitrary value.

            cards.append(ArithmeticOpCard("/"))
            cards.append(LoadCard(tmp_loc))
            cards.append(LoadCard(expr_loc))
            cards.append(CondCard("F", True, len(block)))
            for block_line in block:
                cards.append(block_line)

            free(expr_var)
            free(tmp_var)
            continue

        match = re.match("end", line)
        if match:
            assert(parser_block_depth > 0)
            parser_block_depth -= 1
            break

    lines_read = line_num - init_line_num
    return cards, lines_read

if __name__ == "__main__":
    source = ""

    if len(sys.argv) > 1:
        source_file = sys.argv[1]
        with open(source_file, "r") as f:
            source = f.read()
    else: 
        source = sys.stdin.read()

    cards, num_lines_read = compile(source)
    for card in cards:
        print(card)
