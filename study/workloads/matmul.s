# matmul - dense matrix product C = A * B of two 64 x 64 matrices of 32-bit
# integers. Regular loops, unit-stride and row-stride accesses, a working set
# of 48 KiB (larger than the first-level cache, smaller than the second).
.equ N, 64
.text
main:
    la    s0, mat_a
    la    s1, mat_b
    la    s2, mat_c
    li    s3, N
    li    t0, 0                 # i
init_i:
    li    t1, 0                 # j
init_j:
    slli  t2, t0, 6             # i * N
    add   t2, t2, t1
    slli  t2, t2, 2             # byte offset of element (i, j)
    slli  t3, t1, 1
    add   t3, t3, t0
    addi  t3, t3, 1             # A[i][j] = i + 2j + 1
    add   t4, s0, t2
    sw    t3, 0(t4)
    slli  t3, t0, 1
    add   t3, t3, t0
    sub   t3, t3, t1
    addi  t3, t3, 2             # B[i][j] = 3i - j + 2
    add   t4, s1, t2
    sw    t3, 0(t4)
    addi  t1, t1, 1
    blt   t1, s3, init_j
    addi  t0, t0, 1
    blt   t0, s3, init_i
    li    t0, 0                 # i
mul_i:
    li    t1, 0                 # j
mul_j:
    li    t6, 0                 # accumulator
    slli  a1, t0, 8
    add   a1, s0, a1            # walks row i of A
    slli  a2, t1, 2
    add   a2, s1, a2            # walks column j of B
    li    t2, 0                 # k
mul_k:
    lw    a3, 0(a1)
    lw    a4, 0(a2)
    mulw  a3, a3, a4
    addw  t6, t6, a3
    addi  a1, a1, 4
    addi  a2, a2, 256           # next row of B
    addi  t2, t2, 1
    blt   t2, s3, mul_k
    slli  a5, t0, 8
    slli  a6, t1, 2
    add   a5, a5, a6
    add   a5, s2, a5
    sw    t6, 0(a5)             # C[i][j]
    addi  t1, t1, 1
    blt   t1, s3, mul_j
    addi  t0, t0, 1
    blt   t0, s3, mul_i
    li    a0, 0                 # checksum: a0 = a0 * 31 + C[idx]
    li    t0, 0
    li    t1, 4096
    li    t3, 31
sum:
    lw    t2, 0(s2)
    mul   a0, a0, t3
    add   a0, a0, t2
    addi  s2, s2, 4
    addi  t0, t0, 1
    blt   t0, t1, sum
    ret
.data
.align 6
mat_a: .zero 16384
mat_b: .zero 16384
mat_c: .zero 16384
