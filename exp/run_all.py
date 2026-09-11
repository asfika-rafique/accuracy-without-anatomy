"""Portable 36-run final protocol. --dry-run prints commands without training."""
import argparse, json, subprocess, sys
from pathlib import Path
from _config import RUNS

def grid():
    for seed in range(3):
        for arch, policy, stream, extra in [
            ("densenet201", "grouped", "full", []),
            ("densenet201", "random", "full", []),
            ("resnet50", "grouped", "full", []),
            ("resnet18", "random", "full", []),
            *[("resnet18", "grouped", s, []) for s in ("full", "brain", "nonbrain", "exterior")],
            ("resnet18", "grouped", "full", ["--permute_labels"]),
            *[("resnet18", "grouped", s, ["--exclude_dcm"]) for s in ("full", "nonbrain", "exterior")],
        ]:
            tag=f"{arch}_{policy}_{stream}_s{seed}"
            if "--permute_labels" in extra: tag += "_perm"
            if "--exclude_dcm" in extra: tag += "_nodcm"
            ckpt=arch=="resnet18" and policy=="grouped" and stream=="full" and not extra
            cmd=[sys.executable,str(Path(__file__).with_name("05_train.py")),"--arch",arch,
                 "--policy",policy,"--stream",stream,"--seed",str(seed),"--epochs","15",
                 "--bs","48","--lr","0.0003",*extra]
            if ckpt: cmd.append("--save_ckpt")
            yield tag,cmd,ckpt

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args(); jobs=list(grid())
    if not args.dry_run:
        for tag,cmd,ckpt in jobs:
            record=Path(RUNS)/(tag+".json")
            if record.exists():
                r=json.loads(record.read_text())
                if (r.get("epochs"),r.get("batch_size"),r.get("lr"))!=(15,48,0.0003):
                    raise SystemExit("Stale protocol: "+str(record))
                needed=[Path(RUNS)/(tag+"_preds.npz")]
                if ckpt: needed.append(Path(RUNS)/(tag+".pt"))
                if not all(p.exists() for p in needed):
                    raise SystemExit("Existing summary-only run: "+tag+". Set STROKE_AUDIT_ROOT to a fresh data workspace to retrain; preserve shipped records.")
    for tag,cmd,_ in jobs:
        print(tag+": "+subprocess.list2cmdline(cmd),flush=True)
        if not args.dry_run: subprocess.run(cmd,check=True)
    print(str(len(jobs))+" runs "+("planned; no training performed" if args.dry_run else "completed"))
