"""REST-Schnittstelle für lokale Ausführung und Docker Compose."""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .core import Client, PROVIDERS, ServiceError, extract


def create_server(host, port, output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def send_json(self,status,obj):
            raw=json.dumps(obj,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/health':return self.send_json(200,{'status':'ok'})
            if path=='/laender':return self.send_json(200,PROVIDERS)
            parts=path.strip('/').split('/')
            if len(parts)==3 and parts[0]=='ergebnisse' and len(parts[1])==32 and all(c in '0123456789abcdef' for c in parts[1]) and parts[2] in ('karte.png','grundstueck.json'):
                f=output/parts[1]/parts[2]
                if f.is_file():
                    raw=f.read_bytes();self.send_response(200)
                    self.send_header('Content-Type','image/png' if f.suffix=='.png' else 'application/json; charset=utf-8')
                    self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            self.send_json(404,{'code':'NOT_FOUND'})
        def do_POST(self):
            if urlsplit(self.path).path!='/auszug':return self.send_json(404,{'code':'NOT_FOUND'})
            # Only JSON, bounded bodies, no filesystem paths or source URLs from requests.
            if self.headers.get_content_type()!='application/json':return self.send_json(415,{'code':'JSON_REQUIRED'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('Body muss 1 bis 4096 Bytes enthalten.')
                payload=json.loads(self.rfile.read(length))
                if not isinstance(payload,dict):raise ValueError('JSON-Objekt erforderlich.')
                address=payload.get('adresse');width=payload.get('breite_meter',60)
                if not isinstance(address,str) or not 5<=len(address)<=300:raise ValueError('adresse muss 5 bis 300 Zeichen enthalten.')
                if type(width) not in (int,float):raise ValueError('breite_meter muss eine Zahl sein.')
                if type(payload.get('nur_amtlich',False)) is not bool:raise ValueError('nur_amtlich muss boolesch sein.')
                if not lock.acquire(blocking=False):return self.send_json(429,{'code':'BUSY','meldung':'Ein Abruf läuft bereits.'})
                try:
                    ident=uuid.uuid4().hex
                    result=extract(address,output/ident,width,allow_fallback=not payload.get('nur_amtlich',False),client=Client(output/'.cache'))
                finally:lock.release()
                result['dateien']={'json':f'/ergebnisse/{ident}/grundstueck.json',
                                   'bild':f'/ergebnisse/{ident}/karte.png' if result['bild']['datei'] else None}
                self.send_json(200,result)
            except ServiceError as e:self.send_json(422 if e.code.startswith(('ADDRESS','INVALID')) else 502,{'status':'fehler','code':e.code,'meldung':str(e),'details':e.details})
            except (ValueError,TypeError) as e:self.send_json(400,{'code':'INVALID_REQUEST','meldung':str(e)})
        def log_message(self,*args):pass  # Avoid writing submitted addresses to access logs.
    return ThreadingHTTPServer((host,port),Handler)


def serve(port, output, host='127.0.0.1'):
    server=create_server(host,port,output)
    print(f'Kataster-Service: http://{host}:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
