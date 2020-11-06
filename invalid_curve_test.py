from eccurve import *
import random

sk = random.randrange(1, secp256r1.n)
pk = sk * secp256r1_g


def is_correct(g, d):
    return (d*g).x == (sk*g).x


def validate(d):
    assert d == sk
