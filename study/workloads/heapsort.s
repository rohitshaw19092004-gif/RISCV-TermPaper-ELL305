# heapsort - in-place heap sort of 8192 pseudo-random 64-bit keys (64 KiB).
# Data-dependent branches and accesses that jump around the array.
.equ N, 8192
.text
main:
    mv    s11, ra               # sift is reached with call, so keep ra
    la    s0, arr
    li    s1, N
    li    t0, 0x5851F42D4C957F2D
    li    t1, 0x14057B7EF767814F
    li    t2, 12345             # seed of the generator
    mv    t3, s0
    li    t4, 0
gen:
    mul   t2, t2, t0
    add   t2, t2, t1
    srli  t5, t2, 16
    sd    t5, 0(t3)
    addi  t3, t3, 8
    addi  t4, t4, 1
    blt   t4, s1, gen
    addi  s2, s1, -1            # end = N - 1
    addi  s3, s1, -2
    srli  s3, s3, 1             # start = (N - 2) / 2
heapify:
    mv    a1, s3
    mv    a2, s2
    call  sift
    addi  s3, s3, -1
    bgez  s3, heapify
sortloop:
    blez  s2, sorted
    slli  t0, s2, 3
    add   t0, s0, t0
    ld    t1, 0(t0)             # swap a[end] with a[0]
    ld    t2, 0(s0)
    sd    t2, 0(t0)
    sd    t1, 0(s0)
    addi  s2, s2, -1
    li    a1, 0
    mv    a2, s2
    call  sift
    j     sortloop
sorted:
    li    a0, 0                 # checksum: sum of a[i] * (i + 1)
    li    t0, 0
    mv    t3, s0
chk:
    ld    t1, 0(t3)
    addi  t0, t0, 1
    mul   t1, t1, t0
    add   a0, a0, t1
    addi  t3, t3, 8
    blt   t0, s1, chk
    mv    ra, s11
    ret

# sift(a1 = root, a2 = end): restore the max-heap property below root
sift:
    slli  t0, a1, 1
    addi  t0, t0, 1             # child = 2 * root + 1
    bgt   t0, a2, sift_done
    slli  t1, t0, 3
    add   t1, s0, t1
    ld    t2, 0(t1)             # a[child]
    bge   t0, a2, sift_cmp      # there is no right child
    ld    t3, 8(t1)             # a[child + 1]
    bgeu  t2, t3, sift_cmp
    addi  t0, t0, 1
    addi  t1, t1, 8
    mv    t2, t3
sift_cmp:
    slli  t4, a1, 3
    add   t4, s0, t4
    ld    t5, 0(t4)             # a[root]
    bgeu  t5, t2, sift_done
    sd    t2, 0(t4)
    sd    t5, 0(t1)
    mv    a1, t0
    j     sift
sift_done:
    ret
.data
.align 6
arr: .zero 65536
