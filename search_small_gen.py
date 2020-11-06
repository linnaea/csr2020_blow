import json
from eccurve import *
from math import log2, ceil
from functools import reduce

with open('inval_curves.json', 'r') as f:
    inval_curves = json.load(f)

max_factor = 800
prime_factors = {}
missing_factors = set()
for p in small_primes:
    for i in range(1, ceil(log2(max_factor))):
        f = p ** i
        if f < max_factor:
            missing_factors.add(f)
            prime_factors[p] = i
        else:
            break

sg_count = len(missing_factors)
sg_curves = {}
while len(inval_curves) and missing_factors:
    ks = sorted(inval_curves.keys(), key=lambda v: (-sum(1 for f in inval_curves[v][1] if prime_factors.get(int(f)))))
    b = ks[0]
    gx, factors = inval_curves[b]
    del inval_curves[b]
    print(f'[{len(inval_curves)}/{len(sg_curves)}/{sg_count}] b={b} x={gx} ......\r', end='', flush=True)
    gx = int(gx)
    factors = list(map(int, factors))
    curve = EllipticCurve(secp256r1.a, int(b), secp256r1.mod, reduce(lambda a, v: a*v, factors))
    g = AffinePoint(curve, gx, curve.solve_y(gx, 0))
    sffs = {}
    for f in factors:
        if not prime_factors.get(f):
            continue
        sffs[f] = sffs.get(f, 0) + 1

    for f, n in sffs.items():
        factor = 0
        for i in range(n, 0, -1):
            factor = f ** i
            if factor in missing_factors and str(factor) not in sg_curves:
                gg = curve.n // factor * g
                if factor * gg != curve.poif:
                    continue
                for j in range(1, factor):
                    print(f'[{len(inval_curves)}/{len(sg_curves)}/{sg_count}] b={b} f={factor} x={gg.x} testing {j}....\r',
                          end='', flush=True)
                    if j * gg == curve.poif:
                        gg = None
                        break
                if not gg:
                    continue
                sg_curves[str(factor)] = (str(gg.x), str(gg.y), str(curve.b))
                missing_factors.remove(factor)
                prime_factors[f] -= 1

with open('curve_small_group_generators.json', 'w') as f:
    json.dump(sg_curves, f)

print('')
print(missing_factors)
