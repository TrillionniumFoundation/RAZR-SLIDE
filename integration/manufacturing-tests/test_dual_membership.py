from pathlib import Path
import inspect,sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import contact_dual_active as q

class MembershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=inspect.getsource(q.solve_force_qp)
        new="members=set(F)\n        outside=[i for i in range(free_prefix,m) if i not in members]"
        old="outside=[i for i in range(free_prefix,m) if i not in F]"
        assert source.count(new)==1
        ns=dict(q.__dict__);exec(compile(source.replace(new,old),'<reference-original-membership>','exec'),ns)
        cls.original=staticmethod(ns['solve_force_qp'])
    def test_ordered_complement_matches_original_for_arbitrary_working_sets(self):
        rng=np.random.default_rng(6041)
        for n in range(1,100):
            F=rng.permutation(n)[:n//2].tolist();members=set(F)
            self.assertEqual([i for i in range(n) if i not in F],[i for i in range(n) if i not in members])
    def compare(self,reuse):
        rng=np.random.default_rng(106)
        for k in range(12):
            n=20+k;A=rng.normal(size=(n,n));S=A.T@A+np.eye(n);d=rng.normal(size=n)
            G=np.zeros((n,2));G[:2]=np.eye(2);G[4:]=rng.normal(size=(n-4,2))
            b=np.zeros(2);initial=np.zeros(n)
            a=self.original(S,d,G,b,initial=initial,factor_reuse=reuse)
            z=q.solve_force_qp(S,d,G,b,initial=initial,factor_reuse=reuse)
            self.assertTrue(a['passed']);self.assertTrue(z['passed'])
            self.assertEqual(a,z)
    def test_complete_QP_and_history_match_without_factor_reuse(self):self.compare(False)
    def test_complete_QP_and_history_match_with_factor_reuse(self):self.compare(True)
    def test_duplicate_membership_does_not_change_complement(self):
        F=[5,2,2,0,5];members=set(F)
        self.assertEqual([i for i in range(10) if i not in F],[i for i in range(10) if i not in members])
