# strsearch - naive search for a 6-symbol pattern in 120000 symbols of random
# text over a four-letter alphabet. Short inner loops that end on a
# data-dependent mismatch.
.equ LEN, 120000
.equ PLEN, 6
.text
main:
    la    s0, text
    li    s1, LEN
    li    s3, 0x5851F42D4C957F2D
    li    s4, 0x14057B7EF767814F
    li    t0, 31337             # seed of the generator
    li    t1, 0
gen:
    mul   t0, t0, s3
    add   t0, t0, s4
    srli  t2, t0, 62            # two random bits
    addi  t2, t2, 97            # one of the letters a, b, c, d
    add   t3, s0, t1
    sb    t2, 0(t3)
    addi  t1, t1, 1
    blt   t1, s1, gen
    la    s2, pat               # the pattern is a copy of text[1000..1005]
    li    s6, PLEN
    li    t1, 0
copy:
    add   t3, s0, t1
    lbu   t2, 1000(t3)
    add   t4, s2, t1
    sb    t2, 0(t4)
    addi  t1, t1, 1
    blt   t1, s6, copy
    li    a0, 0
    li    t0, 0                 # i
    addi  s5, s1, -PLEN         # last possible starting position
    li    s7, 31
scan:
    li    t1, 0                 # j
    add   t3, s0, t0
cmp:
    add   t4, t3, t1
    lbu   t5, 0(t4)
    add   t6, s2, t1
    lbu   a1, 0(t6)
    bne   t5, a1, nomatch
    addi  t1, t1, 1
    blt   t1, s6, cmp
    mul   a0, a0, s7            # checksum: a0 = a0 * 31 + (i + 1) per match
    add   a0, a0, t0
    addi  a0, a0, 1
nomatch:
    addi  t0, t0, 1
    ble   t0, s5, scan
    ret
.data
.align 6
pat:  .zero 64
.align 6
text: .zero 120064
