/* rvmodel.c - an RV64IM instruction-set simulator with a first-order timing
 * model of an out-of-order core, written for the ELL 305 term paper
 * "Microarchitectural Security in Modern RISC-V Processors".
 *
 * The functional part executes real RV64IM machine code (the same binaries run
 * unmodified on QEMU). The timing part assigns every dynamic instruction a
 * fetch, dispatch, issue, completion and commit time using a reorder-buffer
 * window model, a three-level cache hierarchy, a TLB and branch predictors.
 * Defenses are modelled as changes to those rules. Wrong-path (transient)
 * execution after a misprediction is simulated explicitly so that its effect
 * on cache state can be counted.
 *
 * Usage: rvmodel prog.bin [prog2.bin] [key=value ...]
 * Build: cc -O2 -std=c11 -Wall -Wextra -o rvmodel rvmodel.c
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint64_t u64; typedef int64_t s64;
typedef uint32_t u32; typedef int32_t s32; typedef uint8_t u8;

#define BASE    0x80000000ULL       /* RAM base of the QEMU 'virt' machine   */
#define MEMSZ   (64u << 20)         /* RAM modelled per domain               */
#define UART    0x10000000ULL
#define FINISH  0x00100000ULL
#define NDOM    2
#define FRAME0  0x80000ULL          /* first physical frame of program RAM   */
#define PTFRAME 0x400000ULL         /* first physical frame of page tables   */
#define NEVER   (~0ULL >> 2)
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))

enum { D_NONE, D_NOSPEC, D_DOM, D_INVE, D_INVV, D_STT, D_NDA, D_UNDO };
enum { P_NONE, P_WAY };
enum { B_GSHARE, B_BIMODAL, B_TAKEN, B_NOTTAKEN };
enum { C_ALU, C_MUL, C_DIV, C_LOAD, C_STORE, C_BR, C_JAL, C_JALR };

/* ------------------------------------------------------------ configuration */
static struct {
    int width, rob, fdepth;                  /* pipeline shape               */
    int l1, l2, llc, mem, mul, div;          /* latencies in cycles          */
    int l1sets, l1ways, l2sets, l2ways, llcsets, llcways, tlbn;
    int repl;                                /* 0 = LRU, 1 = random          */
    int bp, bpbits, btbn, rasn, isolbp;      /* predictors                   */
    int def, fut;                            /* speculation defense, VP model */
    int part, color, flush, flushcost;       /* isolation between domains    */
    int frames;                              /* 1 = scattered page frames    */
    int rnd, rndlat, remap;                  /* randomised LLC index         */
    int wp;                                  /* simulate wrong-path execution */
    u64 quantum, seed, maxinst;
} C = { 4, 128, 4,  4, 14, 45, 220, 3, 20,  64, 8, 512, 8, 2048, 16, 32,  0,
        B_GSHARE, 12, 512, 16, 0,  D_NONE, 0,  P_NONE, 0, 0, 322,  1,  0, 2, 1600,
        1,  0, 1, 2000000000ULL };

static const char *DEFN[] = { "none", "nospec", "dom", "invis-e", "invis-v",
                              "stt", "nda", "undo", 0 };
static const char *BPN[] = { "gshare", "bimodal", "taken", "nottaken", 0 };

/* ----------------------------------------------------------------- machine */
typedef struct {
    u64 x[32], pc, ninst, cycles;
    u8 *mem; int halted, outn; char out[64];
} Hart;
static Hart H[NDOM];

typedef struct {                 /* what one executed instruction did        */
    int cls, rd, rs1, rs2, size, taken;
    u64 addr, npc, tgt;
} Ev;

typedef struct { u64 a, v; int n; } Wsb;      /* wrong-path store buffer     */
static Wsb wsb[64]; static int nwsb;

static u64 rng_state;
static u64 rnd(void)
{
    rng_state ^= rng_state << 13; rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17; return rng_state;
}
static u64 mix(u64 x)            /* stands in for the low-latency cipher     */
{
    x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33;
    x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return x;
}
static int inram(u64 a, int n) { return a >= BASE && a + (u64)n <= BASE + MEMSZ; }

static u64 rdmem(Hart *h, u64 a, int n, int wp)
{
    u64 v = 0;
    memcpy(&v, h->mem + (a - BASE), (size_t)n);
    if (wp)                      /* overlay bytes of buffered transient stores */
        for (int k = 0; k < nwsb; k++)
            for (int b = 0; b < wsb[k].n; b++) {
                u64 o = wsb[k].a + (u64)b - a;
                if (o < (u64)n) {
                    v &= ~(0xffULL << (8 * o));
                    v |= (wsb[k].v >> (8 * b) & 0xff) << (8 * o);
                }
            }
    return v;
}

/* Execute the instruction at pc on register file x. Returns 0 on success, 1 for
 * a bad pc, 2 for an unsupported instruction, 3 for an access outside RAM.
 * With wp=1 the instruction is transient: stores go to a private buffer and
 * nothing architectural is modified except the scratch register file x. */
static int exec(Hart *h, u64 *x, u64 pc, Ev *e, int wp)
{
    if (!inram(pc, 4) || (pc & 3)) return 1;
    u32 in; memcpy(&in, h->mem + (pc - BASE), 4);
    u32 op = in & 127, rd = in >> 7 & 31, f3 = in >> 12 & 7;
    u32 rs1 = in >> 15 & 31, rs2 = in >> 20 & 31, f7 = in >> 25;
    s64 ii = (s32)in >> 20;
    u64 a = x[rs1], b = x[rs2], r = 0;
    e->cls = C_ALU; e->rd = (int)rd; e->rs1 = (int)rs1; e->rs2 = -1;
    e->npc = pc + 4; e->taken = 0; e->tgt = 0; e->addr = 0; e->size = 0;
    switch (op) {
    case 0x37: r = (u64)(s64)(s32)(in & 0xfffff000); e->rs1 = -1; break;
    case 0x17: r = pc + (u64)(s64)(s32)(in & 0xfffff000); e->rs1 = -1; break;
    case 0x6f: {
        s64 o = ((s32)(in & 0x80000000) >> 11) | (s64)(in & 0xff000)
              | (in >> 9 & 0x800) | (in >> 20 & 0x7fe);
        r = pc + 4; e->cls = C_JAL; e->rs1 = -1; e->npc = e->tgt = pc + (u64)o;
        break; }
    case 0x67:
        r = pc + 4; e->cls = C_JALR; e->npc = e->tgt = (a + (u64)ii) & ~1ULL;
        break;
    case 0x63: {
        s64 o = ((s32)(in & 0x80000000) >> 19) | (s64)((in & 0x80) << 4)
              | (in >> 20 & 0x7e0) | (in >> 7 & 0x1e);
        int t;
        switch (f3) {
        case 0: t = a == b; break;            case 1: t = a != b; break;
        case 4: t = (s64)a < (s64)b; break;   case 5: t = (s64)a >= (s64)b; break;
        case 6: t = a < b; break;             case 7: t = a >= b; break;
        default: return 2;
        }
        e->cls = C_BR; e->rd = 0; e->rs2 = (int)rs2; e->taken = t;
        e->tgt = pc + (u64)o; if (t) e->npc = e->tgt;
        break; }
    case 0x03: {
        u64 ad = a + (u64)ii; int n = 1 << (f3 & 3);
        if (f3 == 7) return 2;
        if (!inram(ad, n)) return 3;
        e->cls = C_LOAD; e->addr = ad; e->size = n;
        u64 v = rdmem(h, ad, n, wp);
        switch (f3) {
        case 0: r = (u64)(s64)(int8_t)v; break;
        case 1: r = (u64)(s64)(int16_t)v; break;
        case 2: r = (u64)(s64)(s32)v; break;
        default: r = v;
        }
        break; }
    case 0x23: {
        u64 ad = a + (u64)((s64)((s32)in >> 25) * 32 + (s64)rd);
        int n = 1 << (f3 & 3);
        if (f3 > 3) return 2;
        e->cls = C_STORE; e->rd = 0; e->rs2 = (int)rs2; e->addr = ad; e->size = n;
        if (wp) {
            if (!inram(ad, n) || nwsb == 64) return 3;
            wsb[nwsb].a = ad; wsb[nwsb].v = b; wsb[nwsb++].n = n;
        } else if (inram(ad, n)) {
            memcpy(h->mem + (ad - BASE), &b, (size_t)n);
        } else {                 /* memory-mapped devices of the 'virt' board */
            if (ad == UART) { if (h->outn < 63) h->out[h->outn++] = (char)b; }
            else if (ad == FINISH) h->halted = 1;
            else return 3;
            e->cls = C_ALU;
        }
        break; }
    case 0x13: case 0x1b: {
        int w = op == 0x1b, sh = (int)(in >> 20 & (w ? 31 : 63));
        int ar = in >> 30 & 1;
        switch (f3) {
        case 0: r = a + (u64)ii; break;       case 1: r = a << sh; break;
        case 2: r = (s64)a < ii; break;       case 3: r = a < (u64)ii; break;
        case 4: r = a ^ (u64)ii; break;       case 6: r = a | (u64)ii; break;
        case 7: r = a & (u64)ii; break;
        default:
            if (w) r = ar ? (u64)(s64)((s32)a >> sh) : (u64)((u32)a >> sh);
            else   r = ar ? (u64)((s64)a >> sh) : a >> sh;
        }
        if (w) r = (u64)(s64)(s32)r;
        break; }
    case 0x33: case 0x3b: {
        int w = op == 0x3b;
        e->rs2 = (int)rs2;
        if (f7 == 1 && w) {                       /* RV64M, 32-bit forms      */
            s32 p = (s32)a, q = (s32)b;
            e->cls = f3 < 4 ? C_MUL : C_DIV;
            switch (f3) {
            case 0: r = (u64)(s64)(s32)((u32)p * (u32)q); break;
            case 4: r = q == 0 ? ~0ULL : (p == INT32_MIN && q == -1)
                        ? (u64)(s64)p : (u64)(s64)(p / q); break;
            case 5: r = q == 0 ? ~0ULL : (u64)(s64)(s32)((u32)p / (u32)q); break;
            case 6: r = q == 0 ? (u64)(s64)p : (p == INT32_MIN && q == -1)
                        ? 0 : (u64)(s64)(p % q); break;
            case 7: r = q == 0 ? (u64)(s64)p
                        : (u64)(s64)(s32)((u32)p % (u32)q); break;
            default: return 2;
            }
        } else if (f7 == 1) {                     /* RV64M, 64-bit forms      */
            s64 p = (s64)a, q = (s64)b;
            e->cls = f3 < 4 ? C_MUL : C_DIV;
            switch (f3) {
            case 0: r = a * b; break;
            case 1: r = (u64)(((__int128)p * (__int128)q) >> 64); break;
            case 2: r = (u64)(((__int128)p * (__int128)b) >> 64); break;
            case 3: r = (u64)(((unsigned __int128)a * b) >> 64); break;
            case 4: r = b == 0 ? ~0ULL : (p == INT64_MIN && q == -1)
                        ? a : (u64)(p / q); break;
            case 5: r = b == 0 ? ~0ULL : a / b; break;
            case 6: r = b == 0 ? a : (p == INT64_MIN && q == -1)
                        ? 0 : (u64)(p % q); break;
            default: r = b == 0 ? a : a % b;
            }
        } else {
            int sh = (int)(b & (w ? 31 : 63)), alt = f7 == 0x20;
            switch (f3) {
            case 0: r = alt ? a - b : a + b; break;  case 1: r = a << sh; break;
            case 2: r = (s64)a < (s64)b; break;      case 3: r = a < b; break;
            case 4: r = a ^ b; break;                case 6: r = a | b; break;
            case 7: r = a & b; break;
            default:
                if (w) r = alt ? (u64)(s64)((s32)a >> sh) : (u64)((u32)a >> sh);
                else   r = alt ? (u64)((s64)a >> sh) : a >> sh;
            }
            if (w) r = (u64)(s64)(s32)r;
        }
        break; }
    case 0x0f: e->rd = 0; e->rs1 = -1; break;     /* fence: no functional effect */
    default: return 2;
    }
    if (e->rd) x[e->rd] = r;
    return 0;
}

/* ------------------------------------------------------------------ caches */
typedef struct { u64 tag, ready; u32 lru; u8 valid, owner, ep; } Line;
typedef struct {
    int sets, ways, part, rnd; Line *l;
    u64 key[2], sptr, racc;                  /* randomised-index state       */
    u64 acc, miss, evict, xevict, remapev;   /* statistics                   */
} Cache;
static Cache L1D, L1I, L2, LLC;
static u32 tick;
static int last_wait, last_walk;      /* components of the latest load latency */

static void c_init(Cache *c, int sets, int ways)
{
    c->sets = sets; c->ways = ways;
    c->l = calloc((size_t)sets * (size_t)ways, sizeof(Line));
}
static void c_flush(Cache *c)
{
    for (long i = 0; i < (long)c->sets * c->ways; i++) c->l[i].valid = 0;
}
static u64 c_owned(Cache *c, int dom)        /* lines a domain leaves behind */
{
    u64 n = 0;
    for (long i = 0; i < (long)c->sets * c->ways; i++)
        n += c->l[i].valid && c->l[i].owner == dom;
    return n;
}
static int c_set(Cache *c, u64 line)
{
    u64 m = (u64)c->sets - 1, s;
    if (!c->rnd) return (int)(line & m);
    s = mix(line ^ c->key[0]) & m;           /* current key ...              */
    if (s < c->sptr) s = mix(line ^ c->key[1]) & m;   /* ... or already remapped */
    return (int)s;
}
static void c_range(Cache *c, int dom, int *lo, int *hi)
{
    *lo = 0; *hi = c->ways;
    if (c->part) { *lo = dom * (c->ways / 2); *hi = *lo + c->ways / 2; }
}
static Line *c_find(Cache *c, u64 line, int dom)
{
    int lo, hi; c_range(c, dom, &lo, &hi);
    Line *s = c->l + (size_t)c_set(c, line) * (size_t)c->ways;
    for (int w = lo; w < hi; w++)
        if (s[w].valid && s[w].tag == line) return s + w;
    return 0;
}
static Line *c_victim(Cache *c, int set, int dom)
{
    int lo, hi; c_range(c, dom, &lo, &hi);
    Line *s = c->l + (size_t)set * (size_t)c->ways, *v = s + lo;
    for (int w = lo; w < hi; w++) {
        if (!s[w].valid) return s + w;
        if (s[w].lru < v->lru) v = s + w;
    }
    if (C.repl) v = s + lo + (int)(rnd() % (u64)(hi - lo));
    return v;
}
static void c_fill(Cache *c, u64 line, int dom, u64 ready)
{
    u64 m = (u64)c->sets - 1;
    Line *v = c_victim(c, c_set(c, line), dom);
    if (v->valid) { c->evict++; if (v->owner != dom) c->xevict++; }
    v->valid = 1; v->tag = line; v->owner = (u8)dom; v->lru = ++tick;
    v->ready = ready;
    v->ep = (u8)(c->rnd && (mix(line ^ c->key[0]) & m) < c->sptr);
}
/* One step of gradual remapping: the lines of set sptr move to the sets that
 * the next key assigns them; when every set has been visited the keys rotate. */
static void c_remap(Cache *c)
{
    u64 m = (u64)c->sets - 1;
    Line *s = c->l + (size_t)c->sptr * (size_t)c->ways;
    c->sptr++;
    for (int w = 0; w < c->ways; w++)
        if (s[w].valid && !s[w].ep) {
            Line moved = s[w];
            s[w].valid = 0;
            Line *v = c_victim(c, (int)(mix(moved.tag ^ c->key[1]) & m), moved.owner);
            if (v->valid) c->remapev++;
            *v = moved; v->ep = 1;
        }
    if (c->sptr == (u64)c->sets) {
        c->key[0] = c->key[1]; c->key[1] = rnd(); c->sptr = 0;
        for (long i = 0; i < (long)c->sets * c->ways; i++) c->l[i].ep = 0;
    }
}

/* Access the hierarchy below first-level cache c1 for physical address pa at
 * time t. Returns the latency in cycles and the level that served the access
 * (1 = L1, 2 = L2, 3 = LLC, 4 = memory). With upd=0 nothing is modified. */
static int hier(Cache *c1, u64 pa, int dom, u64 t, int upd, int *lvl)
{
    u64 ln = pa >> 6; Line *p; int lat, lv;
    int extra = LLC.rnd ? C.rndlat : 0;
    if ((p = c_find(c1, ln, dom)))        { lv = 1; lat = C.l1; }
    else if ((p = c_find(&L2, ln, dom)))  { lv = 2; lat = C.l2; }
    else if ((p = c_find(&LLC, ln, dom))) { lv = 3; lat = C.llc + extra; }
    else                                  { lv = 4; lat = C.mem + extra; }
    last_wait = 0;
    if (p && p->ready > t + (u64)lat) {   /* line still in flight: wait for it */
        last_wait = (int)MIN(p->ready - t, (u64)(C.mem + extra)) - lat;
        lat += last_wait;
    }
    if (upd) {
        c1->acc++;
        if (p) p->lru = ++tick;
        if (lv > 1) { c1->miss++; L2.acc++; }
        if (lv > 2) { L2.miss++; LLC.acc++; }
        if (lv > 3) { LLC.miss++; c_fill(&LLC, ln, dom, t + (u64)lat); }
        if (lv > 2) c_fill(&L2, ln, dom, t + (u64)lat);
        if (lv > 1) c_fill(c1, ln, dom, t + (u64)lat);
        if (lv > 2 && LLC.rnd && ++LLC.racc >= (u64)C.remap) {
            LLC.racc = 0; c_remap(&LLC);
        }
    }
    if (lvl) *lvl = lv;
    return lat;
}

/* --------------------------------------------- address translation and TLB */
typedef struct { u64 vpn; u32 lru; u8 valid, asid; } Tlbe;
static Tlbe *tlb;
static u64 tlb_acc, tlb_miss, tlb_xevict;

/* Page frames. Each domain owns 2^14 frames; within them a virtual page is
 * placed either at the same offset (frames=0) or at a pseudo-random one, as a
 * long-running allocator would (frames=1). With colouring a domain receives
 * only frames of its own parity, which halves the sets it can reach in every
 * cache whose way is larger than a page. */
static u64 scatter(int dom, u64 v)            /* a bijection on 14-bit numbers */
{
    v = (v + (C.seed + 7 * (u64)dom) * 0x9e5) & 0x3fff;
    v = v * 0x2c9d & 0x3fff; v ^= v >> 7;
    v = v * 0x1b65 & 0x3fff; v ^= v >> 5;
    return v;
}
static u64 va2pa(int dom, u64 va)
{
    u64 vpn = (va - BASE) >> 12, f = C.frames ? scatter(dom, vpn) : vpn;
    if (C.color) f = FRAME0 + ((u64)dom << 15) + 2 * f + (u64)dom;
    else         f = FRAME0 + ((u64)dom << 14) + f;
    return f << 12 | (va & 4095);
}
static u64 pte_pa(int dom, u64 vpn, int lev)  /* synthetic Sv39 page tables   */
{
    u64 i2 = vpn >> 18 & 511, i1 = vpn >> 9 & 511, i0 = vpn & 511;
    u64 page = lev == 2 ? 0 : lev == 1 ? 1 + i2 : 513 + (i2 * 512 + i1) % 4096;
    u64 idx = lev == 2 ? i2 : lev == 1 ? i1 : i0;
    return (PTFRAME + 2 * page + (u64)dom) << 12 | idx << 3;
}
/* Returns the extra latency of translating va (0 on a TLB hit). */
static int tlb_access(int dom, u64 va, u64 t, int upd)
{
    u64 vpn = va >> 12; int lo = 0, hi = C.tlbn, lat = 0;
    if (C.part) { lo = dom * (C.tlbn / 2); hi = lo + C.tlbn / 2; }
    Tlbe *v = tlb + lo;
    if (upd) tlb_acc++;
    for (int i = lo; i < hi; i++) {
        if (tlb[i].valid && tlb[i].vpn == vpn && tlb[i].asid == dom) {
            if (upd) tlb[i].lru = ++tick;
            return 0;
        }
        if (v->valid && (!tlb[i].valid || tlb[i].lru < v->lru)) v = tlb + i;
    }
    for (int lev = 2; lev >= 0; lev--)        /* three-level walk             */
        lat += hier(&L1D, pte_pa(dom, vpn, lev), dom, t + (u64)lat, upd, 0);
    if (upd) {
        tlb_miss++;
        if (v->valid && v->asid != dom) tlb_xevict++;
        v->valid = 1; v->vpn = vpn; v->asid = (u8)dom; v->lru = ++tick;
    }
    return lat;
}
/* A load's translation plus cache access. hit1 reports a TLB and L1 hit. */
static int dload(int dom, u64 va, u64 t, int upd, int *lvl, int *hit1)
{
    u64 pa = va2pa(dom, va);
    int resident = c_find(&L1D, pa >> 6, dom) != 0;
    int w = tlb_access(dom, va, t, upd);
    if (hit1) *hit1 = resident && w == 0;
    last_walk = w;
    return w + hier(&L1D, pa, dom, t + (u64)w, upd, lvl);
}

/* -------------------------------------------------------- branch predictors */
typedef struct { u64 tag, tgt; u8 valid, owner; } Btbe;
static u8 *pht, *pht_own; static Btbe *btb;
static u32 ghr[NDOM];
static u64 ras[NDOM][64]; static int ras_top[NDOM], ras_cnt[NDOM];
static u64 n_xpred;                           /* predictions from foreign state */

/* With isolbp=1 each domain owns one half of the pattern table and of the
 * target buffer, its own history register and its own return stack. */
static u32 pht_idx(int dom, u64 pc)
{
    u32 g = C.bp == B_GSHARE ? ghr[C.isolbp ? dom : 0] : 0;
    u32 i = ((u32)(pc >> 2) ^ g) & ((1u << C.bpbits) - 1);
    return C.isolbp ? (i >> 1) | (u32)dom << (C.bpbits - 1) : i;
}
static int bp_predict(int dom, u64 pc, int peek)
{
    if (C.bp == B_TAKEN) return 1;
    if (C.bp == B_NOTTAKEN) return 0;
    u32 i = pht_idx(dom, pc);
    if (!peek && pht_own[i] == (u8)(1 - dom)) n_xpred++;
    return pht[i] >= 2;
}
static void bp_update(int dom, u64 pc, int taken)
{
    u32 i = pht_idx(dom, pc); int k = C.isolbp ? dom : 0;
    if (taken && pht[i] < 3) pht[i]++;
    if (!taken && pht[i] > 0) pht[i]--;
    pht_own[i] = (u8)dom;
    ghr[k] = (ghr[k] << 1 | (u32)taken) & ((1u << C.bpbits) - 1);
}
static Btbe *btb_entry(int dom, u64 pc)
{
    u64 i = pc >> 2 & (u64)(C.btbn - 1);
    return btb + (C.isolbp ? (i >> 1) + (u64)(dom * (C.btbn / 2)) : i);
}
static int btb_lookup(int dom, u64 pc, u64 *tgt, int peek)
{
    Btbe *b = btb_entry(dom, pc);
    if (!b->valid || b->tag != pc) return 0;
    if (!peek && b->owner != dom) n_xpred++;
    *tgt = b->tgt;
    return 1;
}
static void btb_update(int dom, u64 pc, u64 tgt)
{
    Btbe *b = btb_entry(dom, pc);
    b->valid = 1; b->tag = pc; b->tgt = tgt; b->owner = (u8)dom;
}
static void ras_push(int dom, u64 a)
{
    int k = C.isolbp ? dom : 0;
    ras[k][ras_top[k]] = a; ras_top[k] = (ras_top[k] + 1) % C.rasn;
    if (ras_cnt[k] < C.rasn) ras_cnt[k]++;
}
static int ras_peek(int dom, int depth, u64 *a)     /* depth 0 = top of stack */
{
    int k = C.isolbp ? dom : 0;
    if (depth >= ras_cnt[k]) return 0;
    *a = ras[k][(ras_top[k] - 1 - depth + 2 * C.rasn) % C.rasn];
    return 1;
}
static int ras_pop(int dom, u64 *a)
{
    int k = C.isolbp ? dom : 0;
    if (!ras_peek(dom, 0, a)) return 0;
    ras_top[k] = (ras_top[k] - 1 + C.rasn) % C.rasn; ras_cnt[k]--;
    return 1;
}
static int is_link(int r) { return r == 1 || r == 5; }
static void bp_flush(void)
{
    memset(pht, 1, (size_t)1 << C.bpbits); memset(pht_own, 255, (size_t)1 << C.bpbits);
    memset(btb, 0, (size_t)C.btbn * sizeof *btb);
    memset(ghr, 0, sizeof ghr); memset(ras_cnt, 0, sizeof ras_cnt);
}

/* ------------------------------------------------------------ timing state */
static u64 reg_rdy[32], reg_tnt[32];   /* value-ready and taint-until times  */
static u64 *rob_c, n_seq;              /* commit times of the last ROB insts */
static u64 f_cyc, d_cyc, c_cyc, br_max, comp_max, last_iline = ~0ULL;
static int f_cnt, d_cnt, c_cnt;
typedef struct { u64 a8, tcomp, tcommit; } Stf;     /* store-to-load forwarding */
static Stf stf[1024];

static struct {
    u64 load, store, br, mis, jalr, jmis, fwd, blocked, second;
    u64 dl_n, dl_sum, dl_lvl[5], dl_walk, dl_wait;
    u64 wp_disp, wp_exec, wp_load, wp_fill, wp_dep, wp_depfill, wp_hidden;
    u64 undo_lines, nswitch, resid[7];
    u64 extra[5];              /* hidden accesses: transient probes, exposures */
} S;

/* Count an access that reached level lv without being a normal cache access. */
static void hidden_access(int lv)
{
    for (int i = 1; i <= lv; i++) S.extra[i]++;
}

/* Simulate the wrong path that starts at wpc after a misprediction. td/cnt is
 * the dispatch slot of the mispredicted instruction and tres the time at which
 * it resolves; an instruction is transient-executed if it issues before tres.
 * Returns the number of first-level fills that completed before the squash,
 * which is what an undo scheme has to roll back. */
static int wrong_path(Hart *h, int dom, u64 wpc, u64 td, int cnt, u64 tres)
{
    u64 x[32], rdy[32], tnt[32], wras[16]; u8 dep[32] = { 0 };
    int nw = 0, rdepth = 0, undo = 0;
    memcpy(x, h->x, sizeof x); memcpy(rdy, reg_rdy, sizeof rdy);
    memcpy(tnt, reg_tnt, sizeof tnt);
    nwsb = 0;
    for (int j = 0; j < C.rob; j++) {
        Ev e;
        if (cnt >= C.width) { td++; cnt = 0; }
        cnt++;
        if (td >= tres || exec(h, x, wpc, &e, 1)) break;
        S.wp_disp++;
        u64 ti = td + 1, tc; int d = 0, lat = 1;
        if (e.rs1 > 0) { ti = MAX(ti, rdy[e.rs1]); d |= dep[e.rs1]; }
        if (e.rs2 > 0) { ti = MAX(ti, rdy[e.rs2]); d |= dep[e.rs2]; }
        u64 next = e.npc;
        if (e.cls == C_LOAD) {
            int lv, hit1, upd = 1, ok;
            int da = e.rs1 > 0 && dep[e.rs1];     /* address from a transient load */
            if (C.def == D_STT) ti = MAX(ti, tnt[e.rs1]);
            if (C.def == D_NOSPEC) ti = MAX(ti, tres);
            dload(dom, e.addr, ti, 0, &lv, &hit1);
            if (C.def == D_DOM && !hit1) ti = MAX(ti, tres);
            ok = ti < tres;
            if (C.def == D_DOM || C.def == D_INVE || C.def == D_INVV
                || C.def == D_UNDO) upd = 0;
            lat = ok ? dload(dom, e.addr, ti, upd, &lv, &hit1) : 1;
            if (ok) {
                S.wp_load++; S.wp_dep += (u64)da;
                if (!hit1 && upd) { S.wp_fill++; S.wp_depfill += (u64)da; }
                if (!upd) hidden_access(lv);
                if (!hit1 && !upd) {      /* a fill that is hidden or rolled back */
                    S.wp_hidden++;
                    undo += C.def == D_UNDO && ti + (u64)lat < tres;
                }
            }
            tc = ok ? ti + (u64)lat : NEVER;
            if (C.def == D_NDA) tc = NEVER;       /* value is never forwarded  */
            if (e.rd) { rdy[e.rd] = tc; dep[e.rd] = 1; tnt[e.rd] = NEVER; }
        } else {
            if (e.cls == C_MUL) lat = C.mul;
            if (e.cls == C_DIV) lat = C.div;
            tc = ti < tres ? ti + (u64)lat : NEVER;
            if (e.rd) {
                rdy[e.rd] = tc; dep[e.rd] = (u8)d;
                tnt[e.rd] = MAX(e.rs1 > 0 ? tnt[e.rs1] : 0, e.rs2 > 0 ? tnt[e.rs2] : 0);
            }
            if (e.cls == C_BR) {                  /* the fetcher follows predictions */
                next = bp_predict(dom, wpc, 1) ? e.tgt : wpc + 4;
            } else if (e.cls == C_JAL || e.cls == C_JALR) {
                if (e.cls == C_JALR && e.rd == 0 && is_link(e.rs1)) {
                    if (nw) next = wras[--nw];
                    else if (!ras_peek(dom, rdepth++, &next)) break;
                } else if (e.cls == C_JALR && !btb_lookup(dom, wpc, &next, 1)) {
                    next = wpc + 4;
                }
                if (is_link(e.rd) && nw < 16) wras[nw++] = wpc + 4;
            }
        }
        if (ti < tres) S.wp_exec++;
        wpc = next;
    }
    return undo;
}

/* Assign times to one committed instruction and update all timing state. */
static void timing(Hart *h, int dom, u64 pc, const Ev *e)
{
    /* fetch: one line of the instruction cache per new line, width per cycle */
    u64 il = va2pa(dom, pc) >> 6;
    if (il != last_iline) {
        int lat = hier(&L1I, il << 6, dom, f_cyc, 1, 0);
        if (lat > C.l1) { f_cyc += (u64)(lat - C.l1); f_cnt = 0; }
        last_iline = il;
    }
    if (f_cnt >= C.width) { f_cyc++; f_cnt = 0; }
    u64 tf = f_cyc; f_cnt++;

    /* dispatch: needs a free reorder-buffer entry, width per cycle */
    u64 td = tf + (u64)C.fdepth, oldest = rob_c[n_seq % (u64)C.rob];
    if (td <= oldest) td = oldest + 1;
    if (td < d_cyc) td = d_cyc;
    if (td == d_cyc && d_cnt >= C.width) td++;
    if (td != d_cyc) { d_cyc = td; d_cnt = 0; }
    d_cnt++;
    if (td - (u64)C.fdepth > f_cyc) { f_cyc = td - (u64)C.fdepth; f_cnt = 1; }
    int dslot = d_cnt;

    /* issue: operands ready */
    u64 ti = td + 1, tnt = 0;
    if (e->rs1 > 0) { ti = MAX(ti, reg_rdy[e->rs1]); tnt = MAX(tnt, reg_tnt[e->rs1]); }
    if (e->rs2 > 0) { ti = MAX(ti, reg_rdy[e->rs2]); tnt = MAX(tnt, reg_tnt[e->rs2]); }
    /* Visibility point: every older control transfer has resolved (Spectre
     * model), or every older instruction has finished executing (Futuristic). */
    u64 vp = C.fut ? comp_max : br_max;
    u64 tcomp, cfloor = 0, redirect = 0;
    int lat = 1, spec = 0, bubble = 0;

    switch (e->cls) {
    case C_LOAD: {
        Stf *s = &stf[e->addr >> 3 & 1023];
        S.load++;
        if (C.def == D_STT && reg_tnt[e->rs1] > ti) { ti = reg_tnt[e->rs1]; S.blocked++; }
        if (C.def == D_NOSPEC && vp > ti) { ti = vp; S.blocked++; }
        if (s->a8 == ((e->addr >> 3) << 1 | (u64)dom) && s->tcommit > ti) {
            lat = (int)(MAX(ti, s->tcomp) - ti) + 1;      /* forwarded from a store */
            spec = vp > ti; S.fwd++;
        } else {
            int lv, hit1;
            if (C.def == D_DOM && vp > ti) {
                dload(dom, e->addr, ti, 0, &lv, &hit1);
                if (!hit1) { ti = vp; S.blocked++; }
            }
            spec = vp > ti;
            lat = dload(dom, e->addr, ti, 1, &lv, &hit1);
            S.dl_n++; S.dl_sum += (u64)lat; S.dl_lvl[lv]++;
            S.dl_walk += (u64)last_walk; S.dl_wait += (u64)last_wait;
            if (spec && (C.def == D_INVE || C.def == D_INVV)) {
                S.second++;                  /* exposure or validation access */
                hidden_access(MIN(lv, 3));
                if (C.def == D_INVV)
                    cfloor = vp + (u64)(lv == 1 ? C.l1 : lv == 2 ? C.l2 : C.llc);
            }
        }
        tcomp = ti + (u64)lat;
        if (e->rd) {
            reg_rdy[e->rd] = (C.def == D_NDA && spec) ? MAX(tcomp, vp) : tcomp;
            reg_tnt[e->rd] = (C.def == D_STT && spec) ? vp : 0;
        }
        break; }
    case C_STORE:
        S.store++;
        tcomp = ti + 1;
        break;
    case C_BR: case C_JALR: {
        u64 tgt = 0, wpc = 0; int mis;
        tcomp = ti + 1;
        u64 tres = C.def == D_STT ? MAX(tcomp, tnt) : tcomp;
        if (e->cls == C_BR) {
            int pred = bp_predict(dom, pc, 0), bhit = btb_lookup(dom, pc, &tgt, 0);
            S.br++;
            mis = pred != e->taken; wpc = pred ? e->tgt : pc + 4;
            bp_update(dom, pc, e->taken);
            if (e->taken) { btb_update(dom, pc, e->tgt); bubble = bhit ? 1 : 3; }
        } else {
            int have;
            S.jalr++;
            if (e->rd == 0 && is_link(e->rs1)) have = ras_pop(dom, &tgt);
            else { have = btb_lookup(dom, pc, &tgt, 0); btb_update(dom, pc, e->tgt); }
            mis = !have || tgt != e->tgt; wpc = have ? tgt : pc + 4;
            if (is_link(e->rd)) ras_push(dom, pc + 4);
            bubble = 1;
            if (e->rd) { reg_rdy[e->rd] = td + 1; reg_tnt[e->rd] = 0; }
        }
        if (mis) {
            int undo = 0;
            if (e->cls == C_BR) S.mis++; else S.jmis++;
            if (C.wp) undo = wrong_path(h, dom, wpc, td, dslot, tres);
            S.undo_lines += (u64)undo;       /* restores run four at a time   */
            redirect = tres + 1 + (u64)((undo + 3) / 4 * C.l2);
            bubble = 0;
        }
        br_max = MAX(br_max, tres); comp_max = MAX(comp_max, tres);
        break; }
    case C_JAL: {
        u64 tgt;
        tcomp = ti + 1;
        bubble = btb_lookup(dom, pc, &tgt, 0) ? 1 : 3;
        btb_update(dom, pc, e->tgt);
        if (is_link(e->rd)) ras_push(dom, pc + 4);
        if (e->rd) { reg_rdy[e->rd] = td + 1; reg_tnt[e->rd] = 0; }
        break; }
    default:
        lat = e->cls == C_MUL ? C.mul : e->cls == C_DIV ? C.div : 1;
        tcomp = ti + (u64)lat;
        if (e->rd) { reg_rdy[e->rd] = tcomp; reg_tnt[e->rd] = tnt; }
    }

    /* commit: in order, width per cycle */
    comp_max = MAX(comp_max, tcomp);
    u64 tc = MAX(tcomp + 1, cfloor);
    if (tc < c_cyc) tc = c_cyc;
    if (tc == c_cyc && c_cnt >= C.width) tc++;
    if (tc != c_cyc) { c_cyc = tc; c_cnt = 0; }
    c_cnt++;
    rob_c[n_seq++ % (u64)C.rob] = tc;

    if (e->cls == C_STORE) {             /* stores write the cache at commit  */
        Stf *s = &stf[e->addr >> 3 & 1023];
        s->a8 = (e->addr >> 3) << 1 | (u64)dom; s->tcomp = tcomp; s->tcommit = tc;
        dload(dom, e->addr, tc, 1, 0, 0);
    }
    if (redirect) { if (redirect > f_cyc) f_cyc = redirect; f_cnt = 0; }
    else if (bubble) { f_cyc += (u64)bubble; f_cnt = 0; }
}

/* ---------------------------------------------------------- context switch */
static void context_switch(int from)
{
    if (C.flush & 1) c_flush(&L1D);
    if (C.flush & 2) c_flush(&L1I);
    if (C.flush & 4) for (int i = 0; i < C.tlbn; i++) tlb[i].valid = 0;
    if (C.flush & 8) bp_flush();
    if (C.flush & 16) c_flush(&L2);
    if (C.flush & 32) c_flush(&LLC);
    S.nswitch++;                         /* state left for the next domain    */
    S.resid[0] += c_owned(&L1D, from); S.resid[1] += c_owned(&L1I, from);
    S.resid[2] += c_owned(&L2, from);  S.resid[3] += c_owned(&LLC, from);
    for (int i = 0; i < C.tlbn; i++) S.resid[4] += tlb[i].valid && tlb[i].asid == from;
    for (int i = 0; i < C.btbn; i++) S.resid[5] += btb[i].valid && btb[i].owner == from;
    for (u32 i = 0; i < (1u << C.bpbits); i++) S.resid[6] += pht_own[i] == from;
    f_cyc = c_cyc + 1 + (u64)(C.flush ? C.flushcost : 0); f_cnt = 0;
    memset(reg_rdy, 0, sizeof reg_rdy); memset(reg_tnt, 0, sizeof reg_tnt);
    last_iline = ~0ULL;
}

static void step(int dom)
{
    Hart *h = &H[dom]; Ev e; u64 pc = h->pc;
    int rc = exec(h, h->x, pc, &e, 0);
    if (rc) {
        fprintf(stderr, "rvmodel: stop %d at pc=%llx, domain %d\n", rc,
                (unsigned long long)pc, dom);
        exit(2);
    }
    h->pc = e.npc; h->ninst++;
    timing(h, dom, pc, &e);
}

static int lookup(const char **names, const char *v)
{
    for (int i = 0; names[i]; i++) if (!strcmp(names[i], v)) return i;
    fprintf(stderr, "rvmodel: unknown value '%s'\n", v); exit(1);
}
static void option(char *arg)
{
    static const struct { const char *k; int *p; } T[] = {
        { "width", &C.width }, { "rob", &C.rob }, { "fdepth", &C.fdepth },
        { "l1", &C.l1 }, { "l2", &C.l2 }, { "llc", &C.llc }, { "mem", &C.mem },
        { "mul", &C.mul }, { "div", &C.div }, { "l1sets", &C.l1sets },
        { "l1ways", &C.l1ways }, { "l2sets", &C.l2sets }, { "l2ways", &C.l2ways },
        { "llcsets", &C.llcsets }, { "llcways", &C.llcways }, { "tlb", &C.tlbn },
        { "repl", &C.repl }, { "bpbits", &C.bpbits }, { "btb", &C.btbn },
        { "ras", &C.rasn }, { "isolbp", &C.isolbp }, { "fut", &C.fut },
        { "part", &C.part }, { "color", &C.color }, { "flush", &C.flush },
        { "flushcost", &C.flushcost }, { "frames", &C.frames }, { "rnd", &C.rnd },
        { "rndlat", &C.rndlat },
        { "remap", &C.remap }, { "wp", &C.wp }, { 0, 0 } };
    char *v = strchr(arg, '=');
    *v++ = 0;
    if (!strcmp(arg, "def")) { C.def = lookup(DEFN, v); return; }
    if (!strcmp(arg, "bp")) { C.bp = lookup(BPN, v); return; }
    if (!strcmp(arg, "quantum")) { C.quantum = strtoull(v, 0, 0); return; }
    if (!strcmp(arg, "seed")) { C.seed = strtoull(v, 0, 0); return; }
    if (!strcmp(arg, "maxinst")) { C.maxinst = strtoull(v, 0, 0); return; }
    for (int i = 0; T[i].k; i++)
        if (!strcmp(T[i].k, arg)) { *T[i].p = atoi(v); return; }
    fprintf(stderr, "rvmodel: unknown option '%s'\n", arg); exit(1);
}

int main(int argc, char **argv)
{
    int nprog = 0, cur = 0;
    for (int i = 1; i < argc; i++) {
        if (strchr(argv[i], '=')) { option(argv[i]); continue; }
        if (nprog == NDOM) { fprintf(stderr, "rvmodel: too many programs\n"); return 1; }
        FILE *f = fopen(argv[i], "rb");
        if (!f) { perror(argv[i]); return 1; }
        H[nprog].mem = calloc(MEMSZ, 1);
        if (!fread(H[nprog].mem, 1, MEMSZ, f)) { fprintf(stderr, "empty image\n"); return 1; }
        fclose(f);
        H[nprog++].pc = BASE;
    }
    if (!nprog) {
        fprintf(stderr, "usage: rvmodel prog.bin [prog2.bin] [key=value ...]\n");
        return 1;
    }
    rng_state = C.seed * 0x9e3779b97f4a7c15ULL + 1;
    c_init(&L1D, C.l1sets, C.l1ways); c_init(&L1I, C.l1sets, C.l1ways);
    c_init(&L2, C.l2sets, C.l2ways);  c_init(&LLC, C.llcsets, C.llcways);
    L1D.part = L1I.part = L2.part = LLC.part = C.part;
    LLC.rnd = C.rnd; LLC.key[0] = rnd(); LLC.key[1] = rnd();
    tlb = calloc((size_t)C.tlbn, sizeof *tlb);
    pht = malloc((size_t)1 << C.bpbits); pht_own = malloc((size_t)1 << C.bpbits);
    btb = calloc((size_t)C.btbn, sizeof *btb);
    rob_c = calloc((size_t)C.rob, sizeof *rob_c);
    bp_flush();

    u64 slice = 0, start = 0, total = 0;
    while (!H[cur].halted && total < C.maxinst) {
        step(cur); slice++; total++;
        int other = 1 - cur, alive = nprog == 2 && !H[other].halted;
        if (H[cur].halted || (C.quantum && slice >= C.quantum && alive)) {
            H[cur].cycles += c_cyc - start;
            if (!alive) break;
            context_switch(cur);
            start = c_cyc; slice = 0; cur = other;
        }
    }
    if (!H[cur].halted) H[cur].cycles += c_cyc - start;

    for (int d = 0; d < nprog; d++) {
        H[d].out[H[d].outn] = 0;
        if (H[d].outn && H[d].out[H[d].outn - 1] == '\n') H[d].out[H[d].outn - 1] = 0;
        printf("out%d=%s inst%d=%llu cyc%d=%llu halted%d=%d ", d, H[d].out, d,
               (unsigned long long)H[d].ninst, d, (unsigned long long)H[d].cycles,
               d, H[d].halted);
    }
#define P(name, v) printf(name "=%llu ", (unsigned long long)(v))
    P("inst", total); P("cycles", c_cyc); P("load", S.load); P("store", S.store);
    P("br", S.br); P("mis", S.mis); P("jalr", S.jalr); P("jmis", S.jmis);
    P("fwd", S.fwd); P("blocked", S.blocked); P("second", S.second);
    P("dl_n", S.dl_n); P("dl_sum", S.dl_sum); P("dl_l1", S.dl_lvl[1]);
    P("dl_l2", S.dl_lvl[2]); P("dl_llc", S.dl_lvl[3]); P("dl_mem", S.dl_lvl[4]);
    P("dl_walk", S.dl_walk); P("dl_wait", S.dl_wait);
    P("l1d_acc", L1D.acc); P("l1d_miss", L1D.miss); P("l1d_xev", L1D.xevict);
    P("l1i_acc", L1I.acc); P("l1i_miss", L1I.miss);
    P("l2_acc", L2.acc); P("l2_miss", L2.miss); P("l2_xev", L2.xevict);
    P("llc_acc", LLC.acc); P("llc_miss", LLC.miss); P("llc_xev", LLC.xevict);
    P("llc_remapev", LLC.remapev);
    P("tlb_acc", tlb_acc); P("tlb_miss", tlb_miss); P("tlb_xev", tlb_xevict);
    P("xpred", n_xpred);
    P("wp_disp", S.wp_disp); P("wp_exec", S.wp_exec); P("wp_load", S.wp_load);
    P("wp_fill", S.wp_fill); P("wp_dep", S.wp_dep); P("wp_depfill", S.wp_depfill);
    P("wp_hidden", S.wp_hidden); P("undo_lines", S.undo_lines);
    P("x_l1", S.extra[1]); P("x_l2", S.extra[2]); P("x_llc", S.extra[3]); P("x_mem", S.extra[4]);
    P("nswitch", S.nswitch); P("res_l1d", S.resid[0]); P("res_l1i", S.resid[1]);
    P("res_l2", S.resid[2]); P("res_llc", S.resid[3]); P("res_tlb", S.resid[4]);
    P("res_btb", S.resid[5]); P("res_pht", S.resid[6]);
    printf("\n");
    return 0;
}
