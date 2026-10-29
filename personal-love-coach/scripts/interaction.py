"""Read-only V4 learning resources. Does not generate predictions or score learners."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def rows(kind):
    return [json.loads(x) for x in (ROOT/'training'/f'interaction-{kind}.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]

def select(kind, key, view='prompt'):
    if kind not in ('capabilities','topics','branches') or view not in ('prompt','study'):
        raise ValueError('Unknown resource or view')
    result=next((x for x in rows(kind) if x['id']==key),None)
    if result is None: raise ValueError('Unknown resource ID')
    if kind=='branches' and view=='prompt':
        return {k:result[k] for k in ('id','scene','input','source_type')}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=('capabilities','topics','branches'))
    parser.add_argument('id')
    parser.add_argument('--view',choices=('prompt','study'),default='prompt')
    args=parser.parse_args()
    try: print(json.dumps(select(args.kind,args.id,args.view),ensure_ascii=False,indent=2))
    except ValueError as e: parser.exit(1,str(e)+'\n')
if __name__=='__main__':main()
