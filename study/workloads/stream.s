# stream - three passes of a[i] = b[i] + 3 c[i] + pass over arrays of 49152
# doublewords (384 KiB each, 1.1 MiB in total). Pure sequential streaming.
.equ N, 49152
.text
main:
    la    s0, arr_a
    la    s1, arr_b
    la    s2, arr_c
    li    s3, N
    li    t0, 0
init:                           # b[i] = i, c[i] = 2i + 1
    slli  t1, t0, 3
    add   t2, s1, t1
    sd    t0, 0(t2)
    slli  t3, t0, 1
    addi  t3, t3, 1
    add   t2, s2, t1
    sd    t3, 0(t2)
    addi  t0, t0, 1
    blt   t0, s3, init
    li    s4, 3                 # passes left
pass:
    mv    t1, s0
    mv    t2, s1
    mv    t3, s2
    li    t0, 0
triad:
    ld    t4, 0(t2)
    ld    t5, 0(t3)
    slli  t6, t5, 1
    add   t5, t5, t6            # 3 * c[i]
    add   t4, t4, t5
    add   t4, t4, s4
    sd    t4, 0(t1)
    sd    t4, 0(t2)             # b[i] = a[i] feeds the next pass
    addi  t1, t1, 8
    addi  t2, t2, 8
    addi  t3, t3, 8
    addi  t0, t0, 1
    blt   t0, s3, triad
    addi  s4, s4, -1
    bnez  s4, pass
    li    a0, 0                 # checksum: a0 = a0 * 31 + a[i]
    li    t0, 0
    li    t6, 31
    mv    t1, s0
sum:
    ld    t4, 0(t1)
    mul   a0, a0, t6
    add   a0, a0, t4
    addi  t1, t1, 8
    addi  t0, t0, 1
    blt   t0, s3, sum
    ret
.data
.align 6
arr_a: .zero 393216
.align 6
arr_b: .zero 393216
.align 6
arr_c: .zero 393216
