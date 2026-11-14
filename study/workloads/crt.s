# crt.s - startup code shared by every kernel.
# Sets up the stack, calls main, prints the 64-bit checksum returned in a0 as
# sixteen hexadecimal digits on the UART, and powers the machine off through
# the test-finisher device. The same code runs on QEMU 'virt' and on rvmodel.
.equ UART,   0x10000000
.equ FINISH, 0x00100000
.text
_start:
    li    sp, 0x83F00000
    call  main
    mv    s0, a0
    li    s1, 60
    li    s2, UART
crt_digit:
    srl   t0, s0, s1
    andi  t0, t0, 15
    addi  t1, t0, -10
    bltz  t1, crt_dec
    addi  t0, t0, 39
crt_dec:
    addi  t0, t0, 48
    sb    t0, 0(s2)
    addi  s1, s1, -4
    bgez  s1, crt_digit
    li    t0, 10
    sb    t0, 0(s2)
    li    t0, FINISH
    li    t1, 0x5555
    sw    t1, 0(t0)
crt_hang:
    j     crt_hang
