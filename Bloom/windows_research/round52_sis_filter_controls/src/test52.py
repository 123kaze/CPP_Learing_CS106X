import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import worker52 as W52
np=W52.np

class Tests(unittest.TestCase):
    def test_fixed_budgets(self):self.assertEqual(W52.budgets(2749058),(672,1343,2685))
    def test_tree_grid_forward_and_restore(self):
        original=W52.RA.candidate_table;seen=[]
        def fake(*args,**kwargs):seen.append(kwargs['trees']);return []
        W52.RA.candidate_table=fake
        try:
            with self.assertRaises(RuntimeError):
                with W52.tree_grid((1,2,4)):
                    W52.RA.candidate_table(None,None,None,1,10,None);raise RuntimeError('fixture')
            self.assertIs(W52.RA.candidate_table,fake);self.assertEqual(seen,[(1,2,4)])
        finally:W52.RA.candidate_table=original
    def test_small_actual_all_selectors_and_controls(self):
        sys.path.insert(0,str(W52.WR/'round43_controlled_catalog/src'))
        import catalog43 as C
        s,X,hashes,_=C.catalogue(2,5299,1024,128,1024);train=s.split['member_train']|s.split['neg_train']
        model=W52.W.lgb.train(W52.S.params(5299,'balanced_clip'),W52.W.lgb.Dataset(X[train],label=s.y[train],weight=W52.S.weights(s.y[train])),num_boost_round=2)
        available=(1,2);scores=W52.W.prefix_raw_scores(model,X,available)
        for t in available:W52.E5.R._MODEL_ARRAYS[s.name,t]=W52.W.model_arrays(model,t)
        learn,tail,_=C.stream(s,'neutral',5299,4000);lm=W52.W.summarize19(learn);qb,qo=W52.E.pack([int(x).to_bytes(8,'little') for x in s.q_ids])
        with W52.E.exact_layout():
            choices=W52.select_all(s,scores,lm,learn,len(tail),8,qb,qo,available)
            self.assertEqual({x[0] for x in choices},set(W52.METHODS))
            for name,c,elapsed,_ in choices:
                self.assertIn(c['trees'],(0,1,2));self.assertLessEqual(W52.ledger(c)['filter_bytes'],8192)
                fp,_,_=W52.E.evaluate(c,tail,s,qb,qo);self.assertGreaterEqual(fp,0)
            ab,ao=W52.E.pack([int(x).to_bytes(8,'little') for x in s.ids])
            controls=W52.fixed_controls(s,scores,lm,len(tail),8,tail,qb,qo,available,(hashes,ab,ao,np.flatnonzero(s.y)))
            self.assertEqual([x['arm'] for x in controls['rows']],['h','traffic','miss'])
            self.assertTrue(all(x['member_BF_FN']==x['final_member_cache_hits']==0 and x['total_bytes']<=8192 for x in controls['rows']))

if __name__=='__main__':unittest.main()
