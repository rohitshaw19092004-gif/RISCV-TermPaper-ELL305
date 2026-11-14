# sieve - sieve of Eratosthenes below 200000 on a byte array. Store-dominated,
# with strides that grow from 2 bytes to hundreds of bytes.
.equ N, 200000
.text
main:
    la    s0, flags
    li    s1, N
    li    t0, 2                 # p
outer:
    mul   t1, t0, t0            # first multiple to cross out is p * p
    bge   t1, s1, count
    add   t2, s0, t0
    lbu   t3, 0(t2)
    bnez  t3, next_p            # p is composite
    li    t4, 1
mark:
    add   t2, s0, t1
    sb    t4, 0(t2)
    add   t1, t1, t0
    blt   t1, s1, mark
next_p:
    addi  t0, t0, 1
    j     outer
count:
    li    a0, 0                 # checksum: the sum of all primes below N
    li    t0, 2
cnt:
    add   t2, s0, t0
    lbu   t3, 0(t2)
    bnez  t3, cnt_next
    add   a0, a0, t0
cnt_next:
    addi  t0, t0, 1
    blt   t0, s1, cnt
    ret
.data
.align 6
flags: .zero 200064
