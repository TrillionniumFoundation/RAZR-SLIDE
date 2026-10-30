"""Order-independent, once-rounded binary64 dot products of finite binary64s.

Each input is an exact dyadic rational. Products and accumulation use Python
integers, followed by one explicitly implemented IEEE-754 nearest/ties-even
rounding. This is a new algorithm identity; it does not reproduce an arbitrary
BLAS reduction's historical last bits. Exact zero is canonical positive zero.
An overflowing final result is rejected instead of returning infinity.
"""
from dataclasses import dataclass
import math
import struct


@dataclass(frozen=True)
class ExactDot:
    value: float
    integer: int
    exponent: int
    nonzero_products: int


def _dyadic(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('finite binary64 inputs required')
    n, d = value.as_integer_ratio()
    return n, -(d.bit_length() - 1)


def _round_integer(n, shift):
    """Round nonnegative n / 2**shift to nearest integer, ties to even."""
    if shift <= 0:
        return n << -shift
    q, r = divmod(n, 1 << shift)
    half = 1 << (shift - 1)
    return q + (r > half or (r == half and (q & 1)))


def round_dyadic64(integer, exponent):
    if type(integer) is not int or type(exponent) is not int:
        raise TypeError('integer dyadic representation required')
    if integer == 0:
        return 0.0
    sign = 1 if integer < 0 else 0
    n = abs(integer)
    power = n.bit_length() - 1 + exponent
    if power < -1022:
        # Includes rounding into the smallest normal value and signed underflow.
        payload = _round_integer(n, -1074 - exponent)
        if payload > (1 << 52):
            raise ArithmeticError('subnormal rounding overflow invariant')
    else:
        significand = _round_integer(n, n.bit_length() - 53)
        if significand == (1 << 53):
            significand >>= 1
            power += 1
        if power > 1023:
            raise OverflowError('exact dot does not round to finite binary64')
        payload = ((power + 1023) << 52) | (significand - (1 << 52))
    return struct.unpack('>d', struct.pack('>Q', (sign << 63) | payload))[0]


def exact_dot64(left, right):
    """Exact products and sum; return one binary64 rounding and its exact value."""
    xs, ys = list(left), list(right)
    if len(xs) != len(ys):
        raise ValueError('dot dimensions differ')
    accumulator = 0
    exponent = 0
    count = 0
    for a, b in zip(xs, ys):
        na, ea = _dyadic(a)
        nb, eb = _dyadic(b)
        term = na * nb
        if term == 0:
            continue
        e = ea + eb
        if not count:
            accumulator, exponent = term, e
        elif e < exponent:
            accumulator = (accumulator << (exponent - e)) + term
            exponent = e
        else:
            accumulator += term << (e - exponent)
        count += 1
    if accumulator:
        trailing = (abs(accumulator) & -abs(accumulator)).bit_length() - 1
        accumulator >>= trailing
        exponent += trailing
    else:
        exponent = 0
    return ExactDot(round_dyadic64(accumulator, exponent), accumulator, exponent, count)
