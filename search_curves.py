# MIRACL/source/mueller 0 400 -o mueller.raw
# MIRACL/source/process -f '(2^32-1).2^224+2^192+2^96-1' -i mueller.raw -o secp256r1.pol
# for r in `seq 0 $(($(nproc)-1))`; do   (for b in `seq $(($r*100+4)) $(($r*100+104))`; do echo $b' '$(nice MIRACL/source/sea -3 $b -i secp256r1.pol | grep NP= | cut -d' ' -f2); done)& done | nice python3 search_curves.py

from eccurve import *
import json

inval_curves = {}
while True:
    try:
        b, n = input().split(' ')
        b, n = int(b), int(n)
    except EOFError:
        break
    except ValueError:
        continue

    curve = EllipticCurve(secp256r1.a, b, secp256r1.mod, n)
    factors = []
    for prime in small_primes:
        while n % prime == 0:
            n //= prime
            factors.append(prime)

    factors.append(n)

    i = 0
    while i < 10:
        try:
            x = random.randrange(1, curve.mod)
            g = AffinePoint(curve, x, curve.solve_y(x, 0))
            print(f"b={b} try={i}......\r", end='', flush=True)

            i += 1
            for factor in set(factors):
                if (curve.n // factor * g) == curve.poif:
                    raise ValueError

            factors = [str(factor) for factor in factors]
            print('')
            print(f'x={g.x}')
            print('n=' + ' * '.join(factors))
            inval_curves[str(b)] = (str(g.x), factors)
            break
        except ValueError:
            continue

with open('inval_curves.json', 'w') as f:
    json.dump(inval_curves, f)
