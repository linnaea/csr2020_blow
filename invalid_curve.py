from eccurve import *
from math import log2
import json
import invalid_curve_test as oracle

with open('curve_small_group_generators.json', 'r') as f:
    sg_points = json.load(f)

d = 0
nd = 0
remainders = {}
search_progress = 0
max_p = max(map(int, sg_points.keys()))
pow_f = {p: False for p in small_primes if p <= max_p}
for p, (ggx, ggy, _) in sorted(sg_points.items(), key=lambda kv: int(kv[0])):
    p, ggx, ggy = int(p), int(ggx), int(ggy)
    for pow_p in pow_f.keys():
        if p % pow_p == 0:
            if pow_f[pow_p]:
                p = 0
            pow_f[pow_p] = True
            break

    if not p:
        continue

    remainders[p] = 0
    g = AffinePoint(secp256r1, ggx, ggy)
    search_top = (p + 1) // 2
    next_progress = log2(reduce(lambda x, y: x * y, remainders.keys())) / log2(secp256r1.n ** 2) * 100
    p_share = next_progress - search_progress
    for d in range(1, search_top + 1):
        ds = (d * d) % p
        print(f'd={d:3}  d^2 mod {p:3} = {ds:3}?  {search_progress + d / search_top * p_share:.3f}% complete\r', end='', flush=True)
        if oracle.is_correct(g, d):
            remainders[p] = ds
            break

    search_progress = next_progress
    print(f'd={d:3}  d^2 mod {p:3} = {remainders[p]:3}   {search_progress:.3f}% complete')
    if search_progress >= 100:
        ds = crt(remainders) % secp256r1.n
        try:
            print(f'd^2={ds}')
            nd = sqrt_mod(ds, secp256r1.n) % secp256r1.n
            if nd and nd * secp256r1_g == oracle.pk:
                print(f'd={nd}')
                break
            nd = (secp256r1.n - nd) % secp256r1.n
            if nd and nd * secp256r1_g == oracle.pk:
                print(f'd={nd}')
                break
        except ValueError:
            pass

oracle.validate(nd)
