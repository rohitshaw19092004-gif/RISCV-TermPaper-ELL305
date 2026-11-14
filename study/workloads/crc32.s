# crc32 - table-driven CRC-32 of a 256 KiB buffer. A sequential stream plus a
# table lookup whose index is derived from the data, the access pattern of
# every table-based cipher.
.equ LEN, 262144
.text
main:
    la    s0, table
    li    s2, 0xEDB88320
    li    s3, 256
    li    t0, 0                 # n
tab_n:
    mv    t1, t0
    li    t2, 8
tab_k:
    andi  t3, t1, 1
    srli  t1, t1, 1
    beqz  t3, tab_skip
    xor   t1, t1, s2
tab_skip:
    addi  t2, t2, -1
    bnez  t2, tab_k
    slli  t4, t0, 2
    add   t4, s0, t4
    sw    t1, 0(t4)
    addi  t0, t0, 1
    blt   t0, s3, tab_n
    la    s1, buf
    li    s4, 0x5851F42D4C957F2D
    li    s5, 0x14057B7EF767814F
    li    t0, 99                # seed of the generator
    li    t1, 32768             # LEN / 8 doublewords
    mv    t2, s1
fillb:
    mul   t0, t0, s4
    add   t0, t0, s5
    sd    t0, 0(t2)
    addi  t2, t2, 8
    addi  t1, t1, -1
    bnez  t1, fillb
    li    a0, 0xFFFFFFFF
    mv    t2, s1
    li    t1, LEN
crc:
    lbu   t3, 0(t2)
    xor   t3, t3, a0
    andi  t3, t3, 255
    slli  t3, t3, 2
    add   t3, s0, t3
    lwu   t4, 0(t3)             # table[(crc ^ byte) & 255]
    srli  a0, a0, 8
    xor   a0, a0, t4
    addi  t2, t2, 1
    addi  t1, t1, -1
    bnez  t1, crc
    not   a0, a0
    slli  a0, a0, 32
    srli  a0, a0, 32            # the CRC is a 32-bit value
    ret
.data
.align 6
table: .zero 1024
.align 6
buf:   .zero 262144
