"""Memoize exact parsing only; preserve every old coordinate/slab predicate."""
from fractions import Fraction as F

_cache = {}


def old_separate(piece, channel):
    key = id(piece)
    saved = _cache.get(key)
    if saved is None:
        B = tuple(tuple(F(x) for x in pair) for pair in piece['box_exact'])
        slabs = tuple((tuple(F(x) for x in s['normal_exact']),
                       tuple(F(x) for x in s['bounds_exact'])) for s in piece['additional_slabs'])
        # Holding the original object prevents an id from being reused.
        saved = (piece, B, slabs)
        _cache[key] = saved
    original, B, slabs = saved
    assert original is piece
    for k in range(3):
        if B[k][1] <= channel[k][0]:
            return str(2*k)
        if B[k][0] >= channel[k][1]:
            return str(2*k+1)
    for normal, bounds in slabs:
        lo = sum((min(normal[k]*channel[k][0],normal[k]*channel[k][1]) for k in range(3)),F(0))
        hi = sum((max(normal[k]*channel[k][0],normal[k]*channel[k][1]) for k in range(3)),F(0))
        if bounds[1] <= lo:
            return '6'
        if bounds[0] >= hi:
            return '7'
    return None
