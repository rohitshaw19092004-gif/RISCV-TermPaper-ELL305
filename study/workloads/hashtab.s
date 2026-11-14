# hashtab - an open-addressing hash table of 16384 sixteen-byte slots (256 KiB):
# 10000 insertions followed by 80000 lookups, of which about one in eight
# finds its key. Random accesses and data-dependent probe loops.
.equ SLOTS, 16384
.equ M, 10000
.equ LOOKUPS, 80000
.text
main:
    la    s0, tab
    li    s3, 0x5851F42D4C957F2D
    li    s4, 0x14057B7EF767814F
    li    s5, 0x9E3779B97F4A7C15    # multiplicative hashing constant
    li    s6, SLOTS - 1
    li    s7, M
    li    t0, 4242              # seed of key stream A
    li    t1, 0                 # i
insert:
    mul   t0, t0, s3
    add   t0, t0, s4
    srli  t2, t0, 20
    ori   t2, t2, 1             # the key; never zero, zero marks a free slot
    mul   t3, t2, s5
    srli  t3, t3, 50            # 14-bit slot number
ins_probe:
    slli  t4, t3, 4
    add   t4, s0, t4
    ld    t5, 0(t4)
    beqz  t5, ins_put
    beq   t5, t2, ins_put
    addi  t3, t3, 1
    and   t3, t3, s6
    j     ins_probe
ins_put:
    sd    t2, 0(t4)
    sd    t1, 8(t4)
    addi  t1, t1, 1
    blt   t1, s7, insert
    li    t0, 4242              # stream A again: its first M keys are present
    li    a1, 1717              # stream B: keys that are almost never present
    li    s8, LOOKUPS
    li    s9, 31
    li    a0, 0
    li    t1, 0                 # q
lookup:
    andi  t6, t1, 1
    bnez  t6, use_b
    mul   t0, t0, s3
    add   t0, t0, s4
    srli  t2, t0, 20
    j     have_key
use_b:
    mul   a1, a1, s3
    add   a1, a1, s4
    srli  t2, a1, 20
have_key:
    ori   t2, t2, 1
    mul   t3, t2, s5
    srli  t3, t3, 50
look_probe:
    slli  t4, t3, 4
    add   t4, s0, t4
    ld    t5, 0(t4)
    beqz  t5, look_miss
    beq   t5, t2, look_hit
    addi  t3, t3, 1
    and   t3, t3, s6
    j     look_probe
look_hit:
    ld    a2, 8(t4)
    addi  a2, a2, 1
    j     look_fold
look_miss:
    li    a2, 0
look_fold:                      # checksum: a0 = a0 * 31 + (value + 1 or 0)
    mul   a0, a0, s9
    add   a0, a0, a2
    addi  t1, t1, 1
    blt   t1, s8, lookup
    ret
.data
.align 6
tab: .zero 262144
