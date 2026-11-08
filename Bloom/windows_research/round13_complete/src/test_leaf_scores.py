import unittest
import numpy as np
import lightgbm as lgb
from leaf_scores import prefix_raw_scores

PREFIXES=(1,2,4,8,12,16,24,32,48,64,96,128,160,200)


class LeafScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(1313)
        cls.X=rng.normal(size=(3000,6)).astype(np.float32)
        cls.y=(cls.X[:,0]+.7*cls.X[:,1]+rng.normal(size=3000)>.4).astype(int)
        cls.model=lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,seed=1,
                                 num_threads=1,deterministic=True,force_col_wise=True,verbose=-1),
                            lgb.Dataset(cls.X,label=cls.y),num_boost_round=200)

    def test_every_prefix_bit_exact(self):
        reference={t:self.model.predict(self.X,raw_score=True,num_iteration=t,num_threads=1) for t in PREFIXES}
        for chunk in (1,127,32768):
            with self.subTest(chunk=chunk):
                got=prefix_raw_scores(self.model,self.X,PREFIXES,chunk)
                for t in PREFIXES:
                    self.assertTrue(np.array_equal(got[t],reference[t]),(chunk,t,np.max(np.abs(got[t]-reference[t]))))

    def test_saved_model_and_missing_values(self):
        model=lgb.Booster(model_str=self.model.model_to_string())
        x=self.X[:101].copy();x[::3,0]=np.nan
        scores=prefix_raw_scores(model,x,(1,32,200),37)
        for t,v in scores.items():
            self.assertTrue(np.array_equal(v,model.predict(x,raw_score=True,num_iteration=t,num_threads=1)))

    def test_empty_rows(self):
        result=prefix_raw_scores(self.model,self.X[:0],(1,200))
        self.assertEqual({t:v.shape for t,v in result.items()},{1:(0,),200:(0,)})

    def test_invalid_inputs(self):
        for prefixes,chunk in (((),1),((0,),1),((201,),1),((1,),0)):
            with self.assertRaises(ValueError):prefix_raw_scores(self.model,self.X,prefixes,chunk)


if __name__=='__main__':
    unittest.main()
