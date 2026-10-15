"""Event model of the drawn R5 dry-loop prototype and forward-only coupon.

Each tick represents delayed counter advance, analog settling and a distinct
sample edge, in that order. This is not SPICE, timing/thermal/physical evidence
or main-return continuity. Actual watchdog and service edges are not invented
when asynchronous reset is removed.
"""
from dataclasses import dataclass,field
from math import inf

@dataclass
class Watchdog:
    now:float=0.0
    last_fall:float=0.0
    asserted_until:float=-inf
    timeout:float=230.0
    reset:float=230.0
    node:bool=False
    assertions:int=0
    stuck_high:bool=False
    @property
    def ok(self):return self.stuck_high or self.now>=self.asserted_until
    def put(self,level):
        level=bool(level);fell=self.node and not level
        if fell and self.ok:self.last_fall=self.now
        self.node=level;return fell and self.ok
    def advance(self,dt):
        end=self.now+dt
        while self.now<end:
            if self.stuck_high:self.now=end;break
            if not self.ok:
                self.now=min(end,self.asserted_until)
                if self.now==self.asserted_until:self.last_fall=self.now
                continue
            expire=self.last_fall+self.timeout
            if expire>end:self.now=end;break
            self.now=expire;self.asserted_until=self.now+self.reset;self.assertions+=1

STATES=((0,0),(1,0),(1,1),(0,1))
EXPECTED=((0,1,1),(1,1,0),(1,0,0),(0,1,1))

@dataclass
class Circuit:
    phase:bool=False
    state:int=0
    valid:list=field(default_factory=lambda:[False]*4)
    tx_pending:bool=False
    tx_armed:bool=False
    rx_pending:list=field(default_factory=lambda:[False,False])
    rx_seen:list=field(default_factory=lambda:[False,False])
    tx_service_level:bool=False
    rx_service_level:bool=False
    tx_pgood:bool=False
    rx_pgood:bool=False
    txwd:Watchdog=field(default_factory=Watchdog)
    phasewd:list=field(default_factory=lambda:[Watchdog() for _ in range(4)])
    rxwd:list=field(default_factory=lambda:[Watchdog(),Watchdog()])
    faults:dict=field(default_factory=dict)
    history:list=field(default_factory=list)
    @property
    def tx_clear(self):return self.tx_pgood and self.txwd.ok and all(w.ok for w in self.phasewd)
    @property
    def rx_clear(self):return self.faults.get('rx_clear_high',False) or (self.rx_pgood and all(w.ok for w in self.rxwd))
    @property
    def qualified(self):return self.tx_clear and self.tx_armed and all(self.valid)
    @property
    def monitor_both_seen(self):return self.faults.get('both_seen_monitor_high',False) or all(self.rx_seen)
    @property
    def final_enable_inputs(self):return [self.rx_pgood and w.ok and seen for w,seen in zip(self.rxwd,self.rx_seen)]
    @property
    def receiver_enabled(self):return all(self.final_enable_inputs)
    @property
    def coupon_powered_ideal_forward(self):
        ea,eb=self.final_enable_inputs
        a=ea or self.faults.get('on_a_high',False) or self.faults.get('switch_a_weld',False)
        b=eb or self.faults.get('on_b_high',False) or self.faults.get('switch_b_weld',False)
        return bool(a and b or self.faults.get('physical_bridge_both_cuts',False))
    def resets(self):
        if not self.tx_clear:self.valid=[False]*4;self.tx_pending=self.tx_armed=False
        if not self.tx_pgood:self.state=0
        for i,w in enumerate(self.rxwd):
            if not (self.rx_pgood and w.ok):self.rx_pending[i]=False;self.rx_seen[i]=False
    def rail(self,tx=None,rx=None):
        if tx is not None:self.tx_pgood=bool(tx)
        if rx is not None:self.rx_pgood=bool(rx)
        self.resets();self.drive_nodes()
    def service(self,tx=None,rx=None):
        if tx is not None:
            if tx and not self.tx_service_level and self.tx_clear:self.tx_pending=True
            self.tx_service_level=bool(tx)
        if rx is not None:
            if rx and not self.rx_service_level:
                for i,w in enumerate(self.rxwd):
                    if self.rx_pgood and w.ok:self.rx_pending[i]=True
            self.rx_service_level=bool(rx)
    def advance(self,dt):
        tx_count=self.txwd.assertions;phase_counts=[w.assertions for w in self.phasewd];rx_counts=[w.assertions for w in self.rxwd]
        self.txwd.advance(dt)
        for w in self.rxwd+self.phasewd:w.advance(dt)
        # Every asynchronous clear pulse matters even after automatic release.
        if self.txwd.assertions!=tx_count or any(w.assertions!=n for w,n in zip(self.phasewd,phase_counts)):
            self.valid=[False]*4;self.tx_pending=self.tx_armed=False
        for i,(w,n) in enumerate(zip(self.rxwd,rx_counts)):
            if w.assertions!=n:self.rx_pending[i]=False;self.rx_seen[i]=False
        self.resets();self.drive_nodes()
    def drive_nodes(self):
        for i,w in enumerate(self.phasewd):w.put((not self.phase) and self.state==i)
        hb=self.phase and all(self.valid)
        hb=self.faults.get('tx_wdi',hb)
        if self.txwd.put(hb) and self.tx_clear:self.tx_armed=self.tx_pending
        levels=[self.phase and self.qualified,(not self.phase) and self.qualified]
        for i,w in enumerate(self.rxwd):
            level=self.faults.get('link_'+str(i),levels[i])
            if w.put(level) and self.rx_pgood and w.ok:self.rx_seen[i]=self.rx_pending[i]
    def sense(self):
        a,b=STATES[self.state]
        selected=b
        if self.faults.get('mux')=='normal':selected=0
        if self.faults.get('mux')=='test':selected=1
        if selected:
            level=self.faults.get('test_drive',a)
            return 3.3 if level else 0.0
        if not a:return 0.0
        if self.faults.get('dry_open'):return 3.3
        if self.faults.get('dry_short'):return 0.0
        return 1.65
    def sample(self):
        v=self.sense();bits=[v>1.32,v<1.98,v<3.3*10/100.9]
        for i,key in enumerate(['lower','upper','low']):
            if key in self.faults:bits[i]=bool(self.faults[key])
        match=tuple(map(int,bits))==EXPECTED[self.state]
        if self.tx_clear:self.valid[self.state]=match
        else:self.resets()
        if 'valid_test_stuck_high' in self.faults:self.valid[2]=True
        return v,bits,match
    def tick(self,half_ms=10.0):
        # Only one Johnson state bit changes after the gated sample clock closes.
        self.phase=True;self.drive_nodes()
        self.advance(.1)  # Explicit assumed propagation/dead-time ordering.
        if self.tx_pgood and not self.faults.get('state_stall'):self.state=(self.state+1)%4
        self.advance(half_ms-.1)
        self.phase=False
        v,bits,match=self.sample();self.drive_nodes()
        self.history.append({'t_ms':self.txwd.now,'state':self.state,'sense_V':v,
          'comparator_bits':list(map(int,bits)),'sample_match':match,
          'all_valid':all(self.valid),'tx_qualified':self.qualified,
          'receiver_enabled':self.receiver_enabled,
          'coupon_powered_ideal_forward':self.coupon_powered_ideal_forward})
        self.advance(half_ms)
    def run(self,ticks=24):
        for _ in range(ticks):self.tick()
        return self

def healthy():
    c=Circuit();c.rail(True,True);c.service(True,True);c.run(8)
    assert c.qualified and c.receiver_enabled and c.coupon_powered_ideal_forward
    return c
