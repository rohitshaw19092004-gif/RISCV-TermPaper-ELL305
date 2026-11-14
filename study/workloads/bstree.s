# bstree - builds an unbalanced binary search tree of 8192 random keys in a
# pool of 32-byte nodes (256 KiB) and performs 30000 lookups. Each step loads
# a key, branches on it unpredictably and then loads a child pointer, so both
# the branch and the next address depend on loaded data.
.equ N, 8192
.equ Q, 30000
.text
main:
    la    s0, pool              # node layout: key, left, right, value
    li    s3, 0x5851F42D4C957F2D
    li    s4, 0x14057B7EF767814F
    li    s5, 5150              # seed of the insertion keys
    li    s6, N
    mul   s5, s5, s3
    add   s5, s5, s4
    srli  t0, s5, 24
    sd    t0, 0(s0)             # the root holds the first key
    sd    zero, 24(s0)
    addi  s1, s0, 32            # next free node
    li    t6, 1                 # number of nodes inserted
insert:
    mul   s5, s5, s3
    add   s5, s5, s4
    srli  t0, s5, 24            # key
    mv    t1, s0                # current node
ins_walk:
    ld    t2, 0(t1)
    beq   t2, t0, ins_next      # duplicate keys are ignored
    bltu  t0, t2, ins_left
    ld    t3, 16(t1)            # right child
    beqz  t3, ins_right
    mv    t1, t3
    j     ins_walk
ins_left:
    ld    t3, 8(t1)             # left child
    beqz  t3, ins_new_left
    mv    t1, t3
    j     ins_walk
ins_new_left:
    sd    s1, 8(t1)
    j     ins_fill
ins_right:
    sd    s1, 16(t1)
ins_fill:
    sd    t0, 0(s1)
    sd    t6, 24(s1)            # value = insertion number
    addi  s1, s1, 32
ins_next:
    addi  t6, t6, 1
    blt   t6, s6, insert
    li    s5, 5150              # even lookups replay the insertion keys ...
    li    s7, 8086              # ... odd lookups use keys that are absent
    li    s8, Q
    li    s9, 31
    li    a0, 0
    li    t6, 0                 # q
lookup:
    andi  t5, t6, 1
    bnez  t5, use_b
    mul   s5, s5, s3
    add   s5, s5, s4
    srli  t0, s5, 24
    j     descend
use_b:
    mul   s7, s7, s3
    add   s7, s7, s4
    srli  t0, s7, 24
descend:
    mv    t1, s0
walk:
    ld    t2, 0(t1)             # key of this node
    beq   t2, t0, found
    bltu  t0, t2, go_left
    ld    t1, 16(t1)
    bnez  t1, walk
    j     absent
go_left:
    ld    t1, 8(t1)
    bnez  t1, walk
absent:
    li    a2, 0
    j     fold
found:
    ld    a2, 24(t1)
    addi  a2, a2, 1
fold:                           # checksum: a0 = a0 * 31 + (value + 1 or 0)
    mul   a0, a0, s9
    add   a0, a0, a2
    addi  t6, t6, 1
    blt   t6, s8, lookup
    ret
.data
.align 6
pool: .zero 262144
