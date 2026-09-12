"""Run and audit a saved timetable without opening Qt or changing the source.

    python3 tools/schedule.py INPUT.roz --seconds 25 --output OUTPUT.roz
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scheduler import solve


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=25)
    parser.add_argument('--seed',type=int,default=17)
    args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():
        parser.error('Çıktı, kaynak dosyadan farklı olmalı.')
    raw=args.input.read_bytes();data=json.loads(raw)
    result=solve(data,time_budget=args.seconds,seed=args.seed)
    data['grid_placements']=result.placements
    data['auto_schedule_results']=result.placements
    data['unplaced_lessons']=result.unplaced
    data['auto_schedule_report']=dict(engine='native-cpp',status=result.status,
        placed_real_hours=result.placed_hours,total_assigned_hours=result.total_hours,
        complete=result.complete,upper_bound=result.upper_bound,
        diagnostics=result.diagnostics,warnings=result.warnings,
        conflicts=result.conflicts,violations=result.violations,
        elapsed_seconds=result.elapsed,seed=args.seed,steps=result.steps,
        source_path=str(args.input.resolve()),source_sha256=hashlib.sha256(raw).hexdigest(),
        unplaced_cards=result.unplaced)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(result.summary())
    for x in result.diagnostics: print(x['message'])
    print(args.output.resolve())
    return 0 if result.complete else 2

if __name__=='__main__':sys.exit(main())
