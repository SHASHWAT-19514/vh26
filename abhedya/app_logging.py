from __future__ import annotations
import json, logging, os, time
from logging.handlers import RotatingFileHandler
from .config import ROOT

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'level':record.levelname,'message':record.getMessage(),'logger':record.name,'pid':os.getpid()},ensure_ascii=False)

def configure_logging():
    path=ROOT/'logs/app.jsonl'; path.parent.mkdir(exist_ok=True)
    handler=RotatingFileHandler(path,maxBytes=50*1024*1024,backupCount=5,encoding='utf-8'); handler.setFormatter(JsonFormatter())
    root=logging.getLogger(); root.setLevel(logging.INFO)
    if not any(isinstance(h,RotatingFileHandler) and getattr(h,'baseFilename','')==str(path) for h in root.handlers): root.addHandler(handler)
    return logging.getLogger('abhedya')
