from __future__ import annotations
import argparse

def main():
    p=argparse.ArgumentParser(prog='python -m abhedya'); sub=p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init'); s=sub.add_parser('serve'); s.add_argument('--host',default='127.0.0.1'); s.add_argument('--port',type=int,default=8000); s.add_argument('--dataset',default=None)
    g=sub.add_parser('synth'); g.add_argument('--rows',type=int,default=10000); g.add_argument('--output',default='data/inbox/demo.csv')
    i=sub.add_parser('ingest'); i.add_argument('csv'); i.add_argument('--dataset-id',default='default')
    args=p.parse_args()
    if args.cmd=='init':
        from .config import ensure_dirs; from .storage import app_db; ensure_dirs(); app_db().close(); print('initialized data directories and SQLite schema')
    elif args.cmd=='serve':
        import os
        if getattr(args,'dataset',None):
            from .ingest import ingest_csv
            from .analytics import analyze
            result=ingest_csv(args.dataset,'default')
            analyze('default')
            os.environ['ABHEDYA_START_DATASET']='default'
            print(result, flush=True)
        import uvicorn; uvicorn.run('abhedya.app:app',host=args.host,port=args.port,workers=1)
    elif args.cmd=='synth':
        from .synth import generate; print(generate(args.output,args.rows)[0])
    elif args.cmd=='ingest':
        from .ingest import ingest_csv; from .analytics import analyze; print(ingest_csv(args.csv,args.dataset_id)); print(analyze(args.dataset_id))
if __name__=='__main__': main()
