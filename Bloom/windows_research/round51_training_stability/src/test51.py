import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stability51 import weights,params,W,np

class Tests(unittest.TestCase):
    def test_balanced_mass_and_mean_weight(self):
        y=np.array([True]*1000+[False]*10);w=weights(y)
        self.assertAlmostEqual(w[y].sum(),w[~y].sum(),places=9);self.assertAlmostEqual(w.mean(),1.,places=12)
        self.assertTrue((w>0).all());self.assertTrue(np.isfinite(w).all())
    def test_missing_class_rejected(self):
        with self.assertRaises(ValueError):weights(np.ones(10,np.bool_))
        with self.assertRaises(ValueError):weights(np.zeros(10,np.bool_))
    def test_clipping_and_label_direction(self):
        rng=np.random.default_rng(5101);y=np.array([True]*1000+[False]*40);X=np.column_stack((y.astype(np.float32),rng.random(len(y)).astype(np.float32)))
        for recipe in ('clip_only','balanced_clip'):
            w=weights(y) if recipe=='balanced_clip' else None
            pos=w[y].sum() if w is not None else y.sum();neg=w[~y].sum() if w is not None else (~y).sum();initial=np.log(pos/neg)
            model=W.lgb.train(params(5101,recipe),W.lgb.Dataset(X,label=y,weight=w),num_boost_round=16)
            score=model.predict(X,raw_score=True,num_threads=1)
            self.assertLessEqual(np.abs(score-initial).max(),1.6+1e-5);self.assertGreater(score[y].mean(),score[~y].mean())

if __name__=='__main__':unittest.main()
