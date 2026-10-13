"""Conditional behavioral model of the R4 drawn hardware, not hardware qualification.

Two actual DFF samples are updated at opposite edges. Each expiry clears both;
the TPS3431 WDO reset delay and automatic release are explicitly represented.
Rail/POR transitions, metastability and analogue component failure dynamics are
not simulated. 'pgood' is a prescribed supervisor boundary, never measurement.
"""
from dataclasses import dataclass
from math import inf

@dataclass
class Probe:
    phase: bool = False
    h: bool = False
    l: bool = False
    pgood: bool = False
    now_ms: float = 0.0
    last_fall_ms: float = 0.0
    wd_until_ms: float = -inf
    wd_timeout_ms: float = 230.0
    wd_reset_ms: float = 230.0
    hb: bool = False
    wd_stuck_high: bool = False
    hb_forced: bool | None = None

    @property
    def wd_ok(self):
        return self.wd_stuck_high or self.now_ms >= self.wd_until_ms

    @property
    def fresh(self):
        return self.pgood and self.wd_ok and self.h and self.l

    def clear(self):
        self.h = self.l = False

    def rail(self, good):
        self.pgood = bool(good)
        if not self.pgood:
            self.clear()
        self.update_heartbeat()

    def update_heartbeat(self):
        new = self.phase and self.h and self.l
        if self.hb_forced is not None:
            new = self.hb_forced
        if self.hb and not new and self.wd_ok:
            self.last_fall_ms = self.now_ms
        self.hb = new

    def advance(self, dt):
        end = self.now_ms + dt
        while self.now_ms < end:
            if self.wd_stuck_high:
                self.now_ms = end
                break
            if self.now_ms < self.wd_until_ms:
                boundary = min(end, self.wd_until_ms)
                self.now_ms = boundary
                if self.now_ms == self.wd_until_ms:
                    # Datasheet automatic WDO release starts a new interval.
                    self.last_fall_ms = self.now_ms
                continue
            expires = self.last_fall_ms + self.wd_timeout_ms
            if expires > end:
                self.now_ms = end
                break
            self.now_ms = expires
            self.wd_until_ms = self.now_ms + self.wd_reset_ms
            self.clear()
            self.update_heartbeat()  # WDI ignored during WDO assertion.
        if not self.pgood or not self.wd_ok:
            self.clear()

    def edge(self, rising, sense_v, *, high_lower_forced=None,
             high_upper_forced=None, low_upper_forced=None):
        # Sense is the pre-edge state. 1nF is drawn to delay its response.
        assert bool(rising) != self.phase
        above = sense_v > 1.32 if high_lower_forced is None else high_lower_forced
        below = sense_v < 1.98 if high_upper_forced is None else high_upper_forced
        low = sense_v < 3.3 * 10 / 100.9 if low_upper_forced is None else low_upper_forced
        self.phase = bool(rising)
        if not self.pgood or not self.wd_ok:
            self.clear()
        elif rising:
            self.l = bool(low and not above)
        else:
            self.h = bool(above and below)
        self.update_heartbeat()

def cycles(p, n=4, *, high=1.65, low=0.0, half_ms=10.0, **faults):
    for _ in range(n):
        if p.phase:
            p.advance(half_ms)
            p.edge(False, high, **faults)
        p.advance(half_ms)
        p.edge(True, low, **faults)
        p.advance(half_ms)
        p.edge(False, high, **faults)
    return p
