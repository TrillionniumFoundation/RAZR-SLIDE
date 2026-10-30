"""Build a replacement subtree before making any mutation to the live tree."""
import copy


def prepare_split(root,node_index,axis,cut,boxes,evaluate,trace):
    before=root['nodes'][node_index]
    trace.update(node_index=node_index,axis=axis,cut_exact=str(cut),completed_children=[])
    children=[]
    for offset,B in enumerate(boxes):
        child=evaluate(B,len(root['nodes'])+offset,before['depth']+1)
        children.append(child);trace['completed_children'].append(child)
    parent=dict(before,kind='split',axis=axis,cut_exact=str(cut),children=[c['id'] for c in children])
    nodes=list(root['nodes']);nodes[node_index]=parent;nodes.extend(children)
    replacement=dict(root,nodes=nodes)
    trace['prepared_complete_replacement']=True
    # The caller commits by assigning this single replacement object. If a
    # signal occurs earlier, the original root and its bound remain valid.
    return replacement


def interruption_controls():
    source={'root_index':0,'nodes':[{'id':0,'depth':0,'kind':'retained','bound_exact':'1'}]}
    controls=[]
    for kind in ('before_first_child','during_second_child','after_both_before_commit'):
        root=copy.deepcopy(source);trace={};calls=[]
        def evaluate(B,index,depth):
            calls.append(index)
            if kind=='before_first_child' or (kind=='during_second_child' and len(calls)==2):
                raise TimeoutError(kind)
            return {'id':index,'depth':depth,'kind':'retained','bound_exact':'1/2'}
        try:
            replacement=prepare_split(root,0,0,'1/2',(None,None),evaluate,trace)
            if kind=='after_both_before_commit':raise TimeoutError(kind)
            raise AssertionError('injection did not occur')
        except TimeoutError as error:
            assert str(error)==kind and root==source
            count={'before_first_child':0,'during_second_child':1,'after_both_before_commit':2}[kind]
            assert len(trace['completed_children'])==count
            controls.append({'case':kind,'original_tree_unchanged':True,'completed_child_diagnostics_preserved':count,'passed':True})
    root=copy.deepcopy(source);trace={}
    replacement=prepare_split(root,0,0,'1/2',(None,None),lambda B,i,d:{'id':i,'depth':d,'kind':'retained','bound_exact':'1/2'},trace)
    assert root==source and len(replacement['nodes'])==3 and replacement['nodes'][0]['children']==[1,2]
    controls.append({'case':'successful_prepare_then_single_reference_commit','original_tree_unchanged_before_commit':True,'passed':True})
    return controls


if __name__=='__main__':
    import json
    from pathlib import Path
    result={'schema':'razr-r9-atomic-refinement-interruption-controls','completed':True,'controls':interruption_controls(),
            'scope':'injected interrupted child construction and before-commit controls; not a full-domain execution'}
    Path(__file__).with_name('ATOMIC_REFINEMENT_INTERRUPTION_CONTROLS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
