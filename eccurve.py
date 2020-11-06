import random
from functools import reduce

small_primes = (
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97,
    101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199,
    211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293,
    307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397,
    401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499,
    503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599,
    601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691,
    701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797,
    809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887,
    907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997,
)


def sqrt_mod(v, n):
    q = (n - 1) // 2
    if pow(v, q, n) != 1:
        raise ValueError

    z = 1
    while pow(z, q, n) == 1:
        z = random.randrange(1, n)

    s = 1
    while not (q & 1):
        s += 1
        q //= 2

    m = s
    c = pow(z, q, n)
    t = pow(v, q, n)
    r = pow(v, q // 2 + 1, n)
    while True:
        if not t:
            return 0
        if t == 1:
            return r
        i = 1
        while i < m:
            if pow(t, pow(2, i, n), n) == 1:
                break
            i += 1

        if i == m:
            raise ValueError

        b = pow(c, pow(2, m - i - 1, n), n)
        m = i
        c = b * b % n
        t = t * b * b % n
        r = r * b % n


def xgcd(a, b):
    prevx, x = 1, 0
    prevy, y = 0, 1
    while b:
        q, r = divmod(a, b)
        x, prevx = prevx - q * x, x
        y, prevy = prevy - q * y, y
        a, b = b, r
    return a, prevx, prevy


def crt(r):
    sum = 0
    prod = reduce(lambda a, b: a * b, r.keys())
    for n_i, a_i in r.items():
        p = prod // n_i
        sum += a_i * (xgcd(p, n_i)[1] % n_i) * p
    return sum % prod


class AffinePoint:

    def __init__(self, curve, x, y):
        self.curve = curve
        self.x = x
        self.y = y

    def __add__(self, other):
        return self.curve.add(self, other)

    def __iadd__(self, other):
        return self.__add__(other)

    def __rmul__(self, scalar):
        return self.curve.mul(self, scalar)

    def __str__(self):
        return "Point({},{}) on {}".format(self.x, self.y, self.curve)

    def copy(self):
        return AffinePoint(self.curve, self.x, self.y)

    def __eq__(self, other):
        if not isinstance(other, AffinePoint):
            raise ValueError("Can't compare Point to {}".format(type(other)))
        return self.curve == other.curve and self.x == other.x and self.y == other.y

    def valid(self):
        return ((self.x ** 3 + self.curve.a * self.x + self.curve.b) % self.curve.mod) == (
                (self.y ** 2) % self.curve.mod)


class EllipticCurve:

    def __init__(self, a, b, p, n):
        """
        Define curve by short weierstrass form y**2 = x**3 + ax + b mod p
        """
        self.a = a
        self.b = b
        self.n = n
        self.mod = p
        self.poif = AffinePoint(self, "infinity", "infinity")

    def inv_val(self, val):
        """
        Get the inverse of a given field element in the curve's prime field.
        """
        return pow(val, self.mod - 2, self.mod)

    def invert(self, point):
        """
        Invert a point.
        """
        return AffinePoint(self, point.x, (-1 * point.y) % self.mod)

    def mul(self, point, scalar):
        """
        Do scalar multiplication Q = dP using double and add.
        """
        return self.double_and_add(point, scalar)

    def double_and_add(self, point, scalar):
        """
        Do scalar multiplication Q = dP using double and add.
        As here: https://en.wikipedia.org/wiki/Elliptic_curve_point_multiplication#Double-and-add
        """
        if scalar < 1:
            raise ValueError("Scalar must be >= 1")
        result = None
        tmp = point.copy()

        while scalar:
            if scalar & 1:
                if result is None:
                    result = tmp
                else:
                    result = self.add(result, tmp)
            scalar >>= 1
            tmp = self.add(tmp, tmp)

        return result

    def add(self, P, Q):
        """
        Sum of the points P and Q.
        Rules: https://en.wikipedia.org/wiki/Elliptic_curve_point_multiplication
        """
        # Cases with POIF
        if P == self.poif:
            result = Q
        elif Q == self.poif:
            result = P
        elif Q == self.invert(P):
            result = self.poif
        else:  # without POIF
            if P == Q:
                slope = (3 * P.x ** 2 + self.a) * self.inv_val(2 * P.y)
            else:
                slope = (Q.y - P.y) * self.inv_val(Q.x - P.x)
            x = (slope ** 2 - P.x - Q.x) % self.mod
            y = (slope * (P.x - x) - P.y) % self.mod
            result = AffinePoint(self, x, y)

        return result

    def solve_y(self, x, lsb):
        rhs = (x ** 3 + self.a * x + self.b) % self.mod
        r = sqrt_mod(rhs, self.mod)
        if not r:
            return 0
        if bool(lsb) != bool(r & 1):
            r = self.mod - r
        return r

    def __str__(self):
        return "y^2 = x^3 + {}x + {} mod {}".format(self.a, self.b, self.mod)


_p = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_a = _p - 3

secp256r1 = EllipticCurve(_a, 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B, _p,
                          0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141)
secp256r1_g = AffinePoint(secp256r1, 48439561293906451759052585252797914202762949526041747995844080717082404635286,
                          36134250956749795798585127919587881956611106672985015071877198253568414405109)
