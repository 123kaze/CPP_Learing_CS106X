"""Raw LightGBM scores for multiple tree prefixes from bounded pred_leaf blocks.

Single-output additive tree models only. The tree order and float64 accumulation
match raw_score prediction; no sigmoid, re-training, pruning or new selection rule.
"""
import numpy as np


def prefix_raw_scores(model, X, prefixes, chunk_rows=32768):
    prefixes=tuple(sorted(set(int(t) for t in prefixes)))
    if not prefixes or min(prefixes)<1 or max(prefixes)>model.num_trees():
        raise ValueError('prefixes must lie within the trained model')
    if chunk_rows<1:
        raise ValueError('chunk_rows must be positive')
    meta=model.dump_model()
    if model.num_model_per_iteration()!=1 or meta.get('average_output',False):
        raise ValueError('Only single-output additive models are supported')
    if any(t['tree_structure'].get('leaf_coeff') for t in meta['tree_info']):
        raise ValueError('Linear-tree models are not supported')
    last=prefixes[-1]
    # Use the API's stored double leaf outputs; tree 0 already contains the initial offset.
    leaf_values=[]
    for tree,t in enumerate(meta['tree_info'][:last]):
        def check(node):
            if 'leaf_value' in node:
                if node.get('leaf_coeff'):
                    raise ValueError('Linear-tree models are not supported')
            else:
                check(node['left_child']);check(node['right_child'])
        check(t['tree_structure'])
        leaf_values.append(np.array([model.get_leaf_output(tree,leaf) for leaf in range(t['num_leaves'])],dtype=np.float64))
    outputs={t:np.empty(len(X),np.float64) for t in prefixes}
    for lo in range(0,len(X),chunk_rows):
        hi=min(len(X),lo+chunk_rows)
        ids=np.asarray(model.predict(X[lo:hi],pred_leaf=True,start_iteration=0,num_iteration=last,num_threads=1))
        if ids.ndim==1:ids=ids.reshape(-1,1)
        if ids.shape!=(hi-lo,last):
            raise ValueError(f'Unexpected leaf-ID shape {ids.shape}')
        total=np.zeros(hi-lo,np.float64)
        for j,values in enumerate(leaf_values):
            total+=values[ids[:,j].astype(np.intp,copy=False)]
            if j+1 in outputs:outputs[j+1][lo:hi]=total
    return outputs
