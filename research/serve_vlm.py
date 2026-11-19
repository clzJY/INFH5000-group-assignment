import argparse,base64,io,json,sys
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from PIL import Image
from vlm_policy import Policy

p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18761);p.add_argument('--adapter',type=Path);p.add_argument('--adapter-root',type=Path);a=p.parse_args()
policy=Policy()
if a.adapter:policy.load(a.adapter)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(b'{"ready":true}')
    def do_POST(self):
        try:
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if a.adapter_root and request['mode'].startswith('lora'):
                seed=next((i for i in (1,2) if f'_s{i}' in request['mode']),0)
                path=a.adapter_root/f'seed{seed}'/'adapter.pt'
                if policy.tag!=str(path):policy.load(path)
            image=Image.open(io.BytesIO(base64.b64decode(request['image']))).convert('RGB')
            result=policy.predict(image,request['mode']);content=json.dumps(result).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(content)
        except Exception as e:
            self.send_response(500);self.end_headers();self.wfile.write(str(e).encode());raise
    def log_message(self,*args):pass
print('VLM_SERVER_READY',flush=True);HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
