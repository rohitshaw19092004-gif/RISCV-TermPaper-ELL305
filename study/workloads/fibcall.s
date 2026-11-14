# fibcall - the doubly recursive Fibonacci function, fib(25). Nearly a quarter
# of a million calls and returns: exercises the return-address stack and
# store-to-load forwarding through the stack frame; no data working set.
.text
main:
    addi  sp, sp, -16
    sd    ra, 8(sp)
    li    a0, 25
    call  fib
    ld    ra, 8(sp)
    addi  sp, sp, 16
    ret
fib:
    li    t0, 2
    blt   a0, t0, fib_base
    addi  sp, sp, -32
    sd    ra, 24(sp)
    sd    s0, 16(sp)
    sd    s1, 8(sp)
    mv    s0, a0
    addi  a0, s0, -1
    call  fib
    mv    s1, a0
    addi  a0, s0, -2
    call  fib
    add   a0, a0, s1
    ld    ra, 24(sp)
    ld    s0, 16(sp)
    ld    s1, 8(sp)
    addi  sp, sp, 32
fib_base:
    ret
