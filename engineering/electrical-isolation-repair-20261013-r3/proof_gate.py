"""Logic of the added physical gates; external probe is not implemented."""
from dataclasses import dataclass
import math
def disconnected_proof_voltage(leakage_each_A,pulldown_ohm):
 if any(type(x) is bool or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in leakage_each_A):raise ValueError('Invalid input leakage')
 if type(pulldown_ohm) is bool or not math.isfinite(pulldown_ohm) or pulldown_ohm<=0:raise ValueError('Invalid pull-down')
 return sum(leakage_each_A)*pulldown_ohm
@dataclass
class ProofGate:
 q:bool=False
 last_arm:bool=False
 def sample(self,pgood,window_ok,probe_fresh,arm):
  if any(type(x) is not bool for x in (pgood,window_ok,probe_fresh,arm)):
   raise ValueError('Inputs must be explicit Boolean observations, not missing/default truthy values')
  clear=pgood and window_ok and probe_fresh
  edge=arm and not self.last_arm
  if not clear:self.q=False
  elif edge:self.q=probe_fresh
  self.last_arm=arm
  return {'async_clear_released':clear,'latch_Q':self.q,'EN_command':self.q and pgood and probe_fresh}
 def reset(self):self.q=False;self.last_arm=False
