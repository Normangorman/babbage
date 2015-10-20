This project is a compiler for a high level programming language, coined BabbageScript, which compiles down into low-level analytical engine instructions.

It provides abstractions including:
* Automatic memory management
* Nested expressions e.g. ((y + 2) / x)
* While loops, if blocks
* Boolean operators (==), (!), (and), (or)

Example BabbageScript program (examples/factorial.bab):

    # computes 7!
    x = 7
    acc = 1

    while !(x == 0)
        acc = (acc * x)
        x = (x - 1)
    end

    print acc

Compiled output:

    N0 7
    N1 1
    N5 0
    +
    L0
    L5
    S4
    N5 0
    -
    L4
    L5
    S6
    /
    L4
    L6
    CF?1
    CF+2
    N3 1
    CF+1
    N3 0
    /
    L3
    L3
    CF?1
    CF+2
    N2 1
    CF+1
    N2 0
    N3 1
    /
    L3
    L2
    CF?35
    N4 0
    +
    L1
    L4
    S3
    N5 0
    +
    L0
    L5
    S4
    *
    L3
    L4
    S1
    N4 0
    +
    L0
    L4
    S3
    N4 1
    -
    L3
    L4
    S0
    CB+72
    N3 0
    +
    L1
    L3
    S2
    N3 0
    +
    L2
    L3
    P

Control flow and boolean operations are implemented using division by 0 to intentionally trigger the run-up lever. The conditional jump card checks if the lever is down, and will jump if so. This allows for a basic form of conditional execution.

The comparison operator (>) currently does not work. It is very tricky to implement due to edge cases with operands being 0 or having different signs.

See [here](https://www.fourmilab.ch/babbage/) for information on the Analytical Engine simulator.
