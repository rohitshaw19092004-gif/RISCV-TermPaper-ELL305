# listwalk - builds a linked list of 16384 nodes, one cache line each (1 MiB),
# threaded in a random order, and walks it six times. Every load address is
# the result of the previous load: the worst case for a memory hierarchy.
.equ N, 16384
.text
main:
    la    s0, perm
    la    s1, nodes
    li    s2, N
    li    t0, 0
init:                           # perm[i] = i
    slli  t1, t0, 2
    add   t1, s0, t1
    sw    t0, 0(t1)
    addi  t0, t0, 1
    blt   t0, s2, init
    li    s3, 0x5851F42D4C957F2D
    li    s4, 0x14057B7EF767814F
    li    s5, 2024              # seed of the generator
    addi  t0, s2, -1            # i = N - 1
shuffle:                        # Fisher-Yates shuffle of perm
    mul   s5, s5, s3
    add   s5, s5, s4
    srli  t1, s5, 33
    addi  t2, t0, 1
    remu  t1, t1, t2            # j = random % (i + 1)
    slli  t3, t0, 2
    add   t3, s0, t3
    slli  t4, t1, 2
    add   t4, s0, t4
    lw    t5, 0(t3)
    lw    t6, 0(t4)
    sw    t6, 0(t3)
    sw    t5, 0(t4)
    addi  t0, t0, -1
    bgtz  t0, shuffle
    li    t0, 0
link:                           # node[perm[k]].next = &node[perm[k + 1]]
    slli  t1, t0, 2
    add   t1, s0, t1
    lwu   t2, 0(t1)
    slli  t3, t2, 6
    add   t3, s1, t3            # address of this node
    slli  t4, t2, 3
    sub   t4, t4, t2
    addi  t4, t4, 1             # payload = 7 * index + 1
    sd    t4, 8(t3)
    addi  t0, t0, 1
    bge   t0, s2, link_last
    lwu   t5, 4(t1)
    slli  t5, t5, 6
    add   t5, s1, t5
    sd    t5, 0(t3)
    j     link
link_last:
    sd    zero, 0(t3)
    li    a0, 0                 # checksum: a0 = a0 * 31 + payload
    li    t6, 31
    li    s6, 6                 # number of passes
    lwu   t0, 0(s0)
    slli  t0, t0, 6
    add   s7, s1, t0            # head of the list
pass:
    mv    t0, s7
walk:
    ld    t1, 8(t0)
    mul   a0, a0, t6
    add   a0, a0, t1
    ld    t0, 0(t0)
    bnez  t0, walk
    addi  s6, s6, -1
    bnez  s6, pass
    ret
.data
.align 6
perm:  .zero 65536
.align 6
nodes: .zero 1048576
