"""Quasi-static lower contact branch for the measured planar cam floor.

The finite-radius pin follows a ramp, a convex floor corner, and a plateau.
A real restoring force is a required boundary condition, not proved by this
model. Engagement at the lower stop has a velocity-slope change; no dynamic
impact, friction, stress, or toleranced fit qualification is asserted.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class ContactProfile:
    pin_radius: float
    floor_height: float
    floor_corner_q: float
    ramp_slope: float
    pin_q: float
    lower_stop_height: float
    q_max: float = 12.0

    def __post_init__(self):
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in asdict(self).values()):
            raise ValueError('profile values must be finite real numbers')
        if self.pin_radius <= 0 or self.ramp_slope <= 0 or self.q_max <= 0:
            raise ValueError('positive pin radius, slope, and travel required')
        a,b,c=self.breakpoints
        if not (0<=a<b<c<self.q_max):
            raise ValueError('profile does not have the four declared ordered branches')
        if self.lower_stop_height >= self.floor_height+self.pin_radius:
            raise ValueError('mechanical stop must be below home pin height')

    @property
    def intercept(self):
        return self.floor_height-self.ramp_slope*self.floor_corner_q+self.pin_radius*math.hypot(1,self.ramp_slope)

    @property
    def breakpoints(self):
        m=self.ramp_slope;r=self.pin_radius
        plateau=self.pin_q-self.floor_corner_q
        rounded=plateau+r*m/math.hypot(1,m)
        engagement=self.pin_q+(self.intercept-self.lower_stop_height)/m
        return plateau,rounded,engagement

    def evaluate(self,q):
        if type(q) not in (int,float) or not math.isfinite(q) or not 0<=q<=self.q_max:
            raise ValueError('q is outside the finite declared cam travel')
        a,b,c=self.breakpoints;x=self.pin_q-q
        if q>=c:return self.lower_stop_height,0.,'lower_stop'
        if q>=b:return self.intercept+self.ramp_slope*x,-self.ramp_slope,'ramp'
        if q<=a:return self.floor_height+self.pin_radius,0.,'plateau'
        dx=x-self.floor_corner_q;radicand=self.pin_radius**2-dx**2
        if radicand<=0:raise ValueError('invalid corner branch, not clamped')
        root=math.sqrt(radicand)
        return self.floor_height+root,dx/root,'rounded_corner'

    def height_bounds(self,q0,q1):
        if q0>q1:raise ValueError('interval must be ordered')
        hi=self.evaluate(q0)[0];lo=self.evaluate(q1)[0]
        return lo,hi

    def receipt(self):
        return {**asdict(self),'breakpoints_q_mm':self.breakpoints,
            'ramp_intercept':self.intercept,'height_range_mm':[self.lower_stop_height,self.floor_height+self.pin_radius],
            'maximum_height_slope_magnitude':self.ramp_slope,
            'selected_branch_requires_lower_restoring_force':True,
            'lower_stop_engagement_is_C0_not_C1':True,
            'rounded_corner_and_plateau_joins_are_C1':True,
            'dynamic_force_friction_and_material_qualification':False,'manufacturing_go':False}
