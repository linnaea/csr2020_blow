# csr.de 2020 `blow`
a.k.a. reason #10007 why you should not roll you own crypto.

## 0. TL;DR:
[Invalid curve attack](https://link.springer.com/chapter/10.1007/978-3-319-24174-6_21)

`/submit` takes [JWE](https://tools.ietf.org/html/rfc7516) in the request body and decrypts it
with the server private key, which is done by calculating the x coordinate of `d * epk`, where
`d` is the private key and `epk` is the public key of the peer(us).

It does not validate that `epk` is actually on the curve and thus can be attacked with this technique.

## 1. Find a curve whose order is composite
The steps are:

1. Pick a `b`
2. Run [SEA](https://en.wikipedia.org/wiki/Schoof%E2%80%93Elkies%E2%80%93Atkin_algorithm)
   on the curve to find the number of points `NP`
3. Factorize `NP` for primes up to some small number

1000 should be able to cover curves up to P-521, 500 for P-256,
there is a list in `eccurve.py`.

[MIRACL](https://github.com/miracl/MIRACL) has an implementation of SEA in C++.

## 2. Find a generator on the curve
Steps are:

1. Generate a random point `g` on the curve
   * This can be done by randomly picking an `x` and solve for `y`
2. Check `NP * g` is the point at inifinity (we'll just call it `infinity`)
3. For each (prime) factor `f` of `NP`: (up to 1000)
   * Check `(NP / f) * g` is not `inifinity`
4. `g` is a generator of the curve.

Note: The chance of the randomly generated point being a generator should be at worst 50%,
      if after a couple tries one cannot be found, generate another curve.

## 3. Find a point in a small subgroup
For each prime factor `f` of `NP`: (up to 1000)
  * Calculate `g_f = (NP / f) * g`, this point is in the subgroup of order `f`

## 4. Improve coverage on small prime numbers
Repeat steps 1-3 until the product of all prime factors is bigger than the curve parameter `p`.

135 unique primes would provide enough coverage for P-521, 77 for P-256.
This probably needs a couple hundred curves to be generated.

There is a list of points that are in a small subgroup that can be used to attack systems
using the P-256 curve in `curve_small_group_generators.json` in the format of `{factor: [x, y, b]}`.
The file is generated from `search_curve.py` and `search_small_gen.py`.

## 5. The oracle that guides us...
Multiplying a point on a elliptic curve would only yield points in the same subgroup.
Since `g_f` is in a small subgroup, there would only be a handful of possible results,
making it possible to calculate and check all of them.

`/submit` will return an error if we guessed the wrong one(different key material, different MAC)
and can be used as the oracle.

Let `P_i = i * g_f` for each `i` in `[1...f-1]`.

In ECDH only the `x` coordinate is used as the shared secret, and for each `x` there are 
usually 2 solutions to the curve equation(`+y` and `-y`), therefore if the server returns
a success to our guess `P_i`, we only know that either `d = i mod f` or `d = -i mod f`.

However, no matter which case is true, `d^2 = i^2 mod f` will always hold.

Trying all different combinations is not a viable solution as it would either require 2^44
tries for the minimum 3831 queries (or 2^20 tries for 198k queries).

Going for `d^2` does require more leaks from the server however, 13490 queries will be needed.

## 6. ...to the private key
Start with the smallest `f` for which you have a corresponding `g_f` to minimize the amount of queries.

For each pair of `f` and `g_f`:
   1. For each `i` in `[1...(f+1) / 2]`:
      1. Pretend to be the server and perform ECDH key derivation using `i` as the private key
         and `g_f` as peer public key, obtain shared secret `x_i`
      2. Encrypt something according to the JWE standard, using `x_i` as the key material
      3. Submit the JWE to the server
      4. If server returns a success, `d^2 = i^2 mod f`
      5. Otherwise continue with the next `i`
   2. If none of the keys tried yields a success then `d^2 = 0 mod f`, `i = 0`.
      * This cannot be checked against the server as the result is `infinity`
        which cannot be serialized to produce a shared secret
   3. Record the factor `f` and the corresponding remainder `i^2`(not `i`)

Note: Only half of the range needs to be checked as the other half are just `-i`s.

Once there are enough residues collected `reduce(lambda x, y: x*y, factors) >= secp256r1.n ** 2`:
   1. Compute `d^2` using the [Chinese remainder theorem](https://en.wikipedia.org/wiki/Chinese_remainder_theorem)
   2. Compute `d` using the [Tonelli–Shanks algorithm](https://en.wikipedia.org/wiki/Tonelli%E2%80%93Shanks_algorithm)
      * This should be done modulo the number of points on P-256
      * There will be 2 solutions `+d` and `-d`, test both
   3. Compute `d*G` with G being the generator point specified in the standard for the P-256 curve
   4. If `d*G` matches the server's public key, `d` is the private key

## 7. Decrypt /juicy.logs
```
kowu doesnt really know how to pwn
lukas2511 just pretends to know networking stuff
manf is actually good in math
CSR{N11111111111111C3_W00rK_Y0u_Curvy_B4st4rd}
```
:)
