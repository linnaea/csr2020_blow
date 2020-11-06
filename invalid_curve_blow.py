from eccurve import *
from jwcrypto import jwk, jwe, jwa
from jwcrypto.common import json_decode, base64url_encode, base64url_decode
import requests
import struct

payload = b"12345678"
pk = AffinePoint(secp256r1,
                 int.from_bytes(base64url_decode("2RntSELMcr5qVFmhWZiCKS0NzkZwm3f0dwbXythHYTw"), 'big'),
                 int.from_bytes(base64url_decode("wJgR6ZgJB6lVZFHF-vQ_biOfOAHuTZayzIE55cCbHEM"), 'big'))
header = {
    "alg": "ECDH-ES",
    "enc": "A128CBC-HS256",
    "kid": "efH3qk1QxpmNvqhY3zXoSEfgml8_7unKoKrvoDIcB1c",
}


class _InvalidEcdh(jwa._EcdhEs):
    name = 'ECDH-ES'
    description = "ECDH-ES using Concat KDF"
    algorithm_usage_location = 'alg'
    algorithm_use = 'kex'
    keysize = None

    def create(self, name):
        return _InvalidEcdh()

    def _derive(self, key, _, alg, bitsize, headers):
        otherinfo = struct.pack('>I', len(alg))
        otherinfo += bytes(alg.encode('utf8'))
        apu = base64url_decode(headers['apu']) if 'apu' in headers else b''
        otherinfo += struct.pack('>I', len(apu))
        otherinfo += apu
        apv = base64url_decode(headers['apv']) if 'apv' in headers else b''
        otherinfo += struct.pack('>I', len(apv))
        otherinfo += apv
        otherinfo += struct.pack('>I', bitsize)
        key = json_decode(key.export(True))
        assert key['kty'] == 'EC'
        assert key['crv'] == 'P-256'
        ggx = int.from_bytes(base64url_decode(key['x']), 'big')
        ggy = int.from_bytes(base64url_decode(key['y']), 'big')
        d = int.from_bytes(base64url_decode(key['d']), 'big')
        shared_key = (d * AffinePoint(secp256r1, ggx, ggy)).x.to_bytes(32, 'big')

        ckdf = jwa.ConcatKDFHash(algorithm=jwa.hashes.SHA256(),
                                 length=jwa._inbytes(bitsize),
                                 otherinfo=otherinfo,
                                 backend=self.backend)
        return ckdf.derive(shared_key)

    def wrap(self, key, bitsize, cek, headers):
        dk_size = self.keysize
        if self.keysize is None:
            if cek is not None:
                raise jwe.InvalidJWEOperation('ECDH-ES cannot use an existing CEK')
            alg = headers['enc']
            dk_size = bitsize
        else:
            alg = headers['alg']

        dk = self._derive(key, key, alg, dk_size, headers)
        if self.keysize is None:
            ret = {'cek': dk}
        else:
            aeskw = self.aeskwmap[self.keysize]()
            kek = jwk.JWK(kty="oct", use="enc", k=base64url_encode(dk))
            ret = aeskw.wrap(kek, bitsize, cek, headers)

        ret['header'] = {'epk': json_decode(key.export_public())}
        return ret


jwe.JWE._jwa_keymgmt = _InvalidEcdh.create


def is_correct(g, d):
    k = jwk.JWK(kty='EC', crv='P-256',
                d=base64url_encode(d.to_bytes(2, 'big')),
                x=base64url_encode(g.x.to_bytes(32, 'big')),
                y=base64url_encode(g.y.to_bytes(32, 'big')))

    probe = jwe.JWE(payload, recipient=k, protected=header).serialize(True)
    response = requests.post('http://chal.cybersecurityrumble.de:1234/submit', probe.encode())
    return response.content == b'{"status":"success"}\n'


def validate(d):
    k = jwk.JWK(kty='EC', crv='P-256',
                d=base64url_encode(d.to_bytes(2, 'big')),
                x='2RntSELMcr5qVFmhWZiCKS0NzkZwm3f0dwbXythHYTw',
                y='wJgR6ZgJB6lVZFHF-vQ_biOfOAHuTZayzIE55cCbHEM')

    messages = """
    eyJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiRUNESC1FUyIsImtpZCI6ImVmSDNxazFReHBtTnZxaFkzelhvU0VmZ21sOF83dW5Lb0tydm9ESWNCMWMiLCJlcGsiOnsia3R5IjoiRUMiLCJjcnYiOiJQLTI1NiIsIngiOiJHUmloUzl6SDVTZEpvU3EwenFwYWdwR3JnMXRRUnZNZk9sZjlKYXprMHFBIiwieSI6IlRNYWpSemFfZkIwTTdqUnhqbmtJZV9DY0xCeERJTmprajhRWHlfUUF4MWsifX0..orAbmerNQliZG9-nVYrHCw.KUV7IoIm_zDtQu7hQ6nZiRxi3DtxYUtVpVAcu21HkJJoTZrB7QOi5YuBR5HGJn2v.ZTSV1ognrDjsfHycJYCaFg
    eyJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiRUNESC1FUyIsImtpZCI6ImVmSDNxazFReHBtTnZxaFkzelhvU0VmZ21sOF83dW5Lb0tydm9ESWNCMWMiLCJlcGsiOnsia3R5IjoiRUMiLCJjcnYiOiJQLTI1NiIsIngiOiJ3Uk50ejVKUHZ6azJnQkhVUXZDNTBWQ2RFSG9lNEp4OEpNUUN3N1BvREN3IiwieSI6IlVNcWVmUzlGOUJNM2dlc0hselZURmNfdGw1UmpENEV1TUJoeEx5ZHZ2alUifX0..QP7f5kKOjEMM8AxQIA5y5g.tP3tqZg33rL1zP4dv7yd8nn7cM-IAfwTJmr2VmYLEI_8b9F0COF4_hJ2b5_NqkoMlg_xxOdUF3XmpSbVcAc_8A.ny62Y_phyge1fUobqzI80g
    eyJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiRUNESC1FUyIsImtpZCI6ImVmSDNxazFReHBtTnZxaFkzelhvU0VmZ21sOF83dW5Lb0tydm9ESWNCMWMiLCJlcGsiOnsia3R5IjoiRUMiLCJjcnYiOiJQLTI1NiIsIngiOiJZTDViOG1kYUNwc2pmdm1VeDFic3ZUX1ZyNUFCMktsSXA3YlpYWkk2MjJnIiwieSI6IjdabmhjWnExbEFIRHFLM0NEX3dYWjRObkExNkQ2U296LXZJekQ5Q0RyaTAifX0..GNy5kvNY4sP_xbfyCwsneg.XgDgFwdAteV4jGvwTZHTPmjzYnEL6DHnRZ4urQaBbXs.8PaSpUQ832hl6_43mlA1Bw
    eyJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiRUNESC1FUyIsImtpZCI6ImVmSDNxazFReHBtTnZxaFkzelhvU0VmZ21sOF83dW5Lb0tydm9ESWNCMWMiLCJlcGsiOnsia3R5IjoiRUMiLCJjcnYiOiJQLTI1NiIsIngiOiJhclJEa1M1UnRfWGk1N2VraUdjYlBRM1B1a21Nb3U5Y2swYmw1SzBrWDh3IiwieSI6IjhwaXFUdU1Kd3Q4WHQ4WklwSmJYOG1zVjVEM2lqRHNtcnV5MV9kNDc2aDgifX0..GOGg4Bu-sUgj2ywK2hFqUQ.fi90qNDVYlvUxHsWVtsI1jjgbO0nnt1BBslEOWyUeWGFUg2IEX2jhczdfnE1r73m.avggzq3ZmTx6Yg9eldPnvQ
    """.splitlines(False)

    for message in messages:
        if not message:
            continue

        m = jwe.JWE()
        m.deserialize(message, k)
        print(m.plaintext)
