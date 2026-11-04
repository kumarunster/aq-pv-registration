import argparse
import json
import sys
from pathlib import Path
from .core import Client, PROVIDERS, ServiceError, extract


def main():
    p=argparse.ArgumentParser(description='Adresse → Katasterbild (standardmäßig 60 m) und Grundstücks-JSON')
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('auszug');q.add_argument('adresse');q.add_argument('-o','--output',default='ergebnis')
    q.add_argument('--breite-meter',type=float,default=60);q.add_argument('--nur-amtlich',action='store_true')
    s=sub.add_parser('serve');s.add_argument('--port',type=int,default=8765);s.add_argument('--output',default='ergebnisse')
    s.add_argument('--host',default='127.0.0.1',help='Bind-Adresse; im Container 0.0.0.0 verwenden')
    sub.add_parser('laender')
    args=p.parse_args()
    if args.command=='laender':
        print(json.dumps(PROVIDERS,ensure_ascii=False,indent=2));return
    if args.command=='serve':
        from .server import serve
        serve(args.port,Path(args.output),host=args.host);return
    try:
        result=extract(args.adresse,args.output,args.breite_meter,allow_fallback=not args.nur_amtlich,
                       client=Client(Path(__file__).resolve().parents[1]/'.cache'))
        print(json.dumps({'status':result['status'],'bild':str(Path(args.output)/'karte.png') if result['bild']['datei'] else None,
                          'json':str(Path(args.output)/'grundstueck.json'),'grundstuecke':result['grundstuecke'],
                          'hinweise':result['hinweise']},ensure_ascii=False,indent=2))
    except ServiceError as e:
        print(json.dumps({'status':'fehler','code':e.code,'meldung':str(e),'details':e.details},ensure_ascii=False,indent=2),file=sys.stderr)
        sys.exit(2)

if __name__=='__main__':main()
