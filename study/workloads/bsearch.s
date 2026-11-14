# bsearch - 16000 binary searches in a sorted table of 65536 keys (512 KiB).
# The compare-and-branch in the loop is essentially unpredictable, and each
# wrong guess starts a load from the wrong half of the table.
.equ N, 65536
.equ Q, 16000
.text
main:
    la    s0, keys
    li    s1, N
    li    t0, 0
    li    t1, 1
    mv    t2, s0
fill:                           # keys[i] = 3i + 1, sorted by construction
    sd    t1, 0(t2)
    addi  t1, t1, 3
    addi  t2, t2, 8
    addi  t0, t0, 1
    blt   t0, s1, fill
    li    s3, 0x5851F42D4C957F2D
    li    s4, 0x14057B7EF767814F
    li    s5, 777               # seed of the generator
    li    s6, Q
    li    s7, 196608            # 3N: range of the query keys
    li    s8, 31
    li    a0, 0
query:
    mul   s5, s5, s3
    add   s5, s5, s4
    srli  t0, s5, 40
    remu  t0, t0, s7            # the key to look for
    li    t1, 0                 # lo
    addi  t2, s1, -1            # hi
search:
    bgt   t1, t2, miss
    add   t3, t1, t2
    srli  t3, t3, 1             # mid
    slli  t4, t3, 3
    add   t4, s0, t4
    ld    t5, 0(t4)
    beq   t5, t0, hit
    bltu  t5, t0, right
    addi  t2, t3, -1            # hi = mid - 1
    j     search
right:
    addi  t1, t3, 1             # lo = mid + 1
    j     search
hit:
    addi  t6, t3, 1
    j     fold
miss:
    li    t6, 0
fold:                           # checksum: a0 = a0 * 31 + (index + 1 or 0)
    mul   a0, a0, s8
    add   a0, a0, t6
    addi  s6, s6, -1
    bnez  s6, query
    ret
.data
.align 6
keys: .zero 524288
