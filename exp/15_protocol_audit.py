"""Fail-closed validation of all 36 final run records; no data or training needed."""
import json, math
from pathlib import Path
from _config import RUNS
from run_all import grid

def main():
    files=list(Path(RUNS).glob("*.json")); expected={tag for tag,_,_ in grid()}
    actual={p.stem for p in files}; errors=[]; splits={}
    if actual!=expected: errors.append(f"Run grid mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
    for p in sorted(files):
        r=json.loads(p.read_text()); tag=p.stem
        for k,v in {"epochs":15,"batch_size":48,"lr":0.0003}.items():
            if r.get(k)!=v: errors.append(f"{tag}: {k}={r.get(k)}, expected {v}")
        inferred=f"{r['arch']}_{r['policy']}_{r['stream']}_s{r['seed']}"+("_perm" if r['permuted_labels'] else "")+("_nodcm" if r.get('exclude_dcm') else "")
        if inferred!=tag: errors.append(tag+": configuration/tag mismatch")
        h=r.get('history',[])
        if len(h)!=15 or not 1<=r.get('best_epoch',0)<=15: errors.append(tag+": epoch history mismatch")
        elif not math.isclose(h[r['best_epoch']-1]['val_macro_f1'],max(x['val_macro_f1'] for x in h),abs_tol=1e-12): errors.append(tag+": selected epoch not validation-F1 maximum")
        size=tuple(r[k] for k in ('n_train','n_val','n_test'))
        if sum(size)!=(6773 if r.get('exclude_dcm') else 7202): errors.append(tag+": wrong slice total")
        key=(r['policy'],r['seed'],bool(r.get('exclude_dcm')))
        if key in splits and splits[key]!=size: errors.append(tag+": inconsistent split sizes")
        splits[key]=size
        if r['policy']=='grouped' and r['test_by_leakage']['leaked']['n']!=0: errors.append(tag+": grouped test leakage")
    if errors: raise SystemExit("FAIL\n"+"\n".join(errors))
    print(f"PASS: {len(files)} records; complete 12-configuration x 3-seed grid; 15 epochs, batch 48, lr 3e-4; validation selection, split sizes and grouped leakage checked.")
    print("Record checks do not establish patient separation, hidden implementation equivalence, or bitwise reproducibility.")

if __name__=='__main__': main()
