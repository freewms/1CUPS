#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import logging
import cups
import base64
import markdown
import json
import jsonschema
from jsonschema import ValidationError
from json import JSONDecodeError

json_schema = json.loads(open("schema.json", "r").read())
fout = open("favicon.ico", "rb").read()
text_help = open("README.md", "r", encoding="utf-8").read()
loglevel = logging.INFO

class S(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args):
        logging.debug('Call: {0}'.format(args))
           
    def do_GET(self):
        if self.path == '/favicon.ico':
            msg = ResponseMsg(200)
            msg.setContentType('image/jpeg')
            msg.setBody(fout)
            self.send_reply(msg)
            return
        msg = ResponseMsg(200)
        msg.setContentType('text/html')
        msg.setBody(markdown.markdown(text_help, output_format='html'))
        self.send_reply(msg)

    def do_POST(self):
        try:
            content_type = self.headers.get_content_type()
            if content_type != 'application/json':
                raise Exception('Content-Type header is application/json required')
            content_length = self.headers.get('Content-Length')
            if content_length == None:
                raise Exception('Content-Length header is required')
            payload = self.rfile.read(int(content_length)).decode('utf-8')
            json_data = json.loads(payload)
            jsonschema.validate(json_data, json_schema)
            msg = postCommandSelector(json_data)
        except (ValidationError, JSONDecodeError) as e:
            msg = ResponseMsg(400)
            msg.setBody(str(e.args[0]))
        except Exception as e:
            msg = ResponseMsg(400)
            msg.setBody(str(e.args[0]))
        self.send_reply(msg)
  
    def send_reply(self, msg):
        if msg.code != 200:
            self.send_error(msg.code, msg.body)
        else:
            self.send_response(msg.code)
            if msg.contentType == None:
                self.send_header('Content-type text/plain;charset=utf-8')
            else:
                self.send_header('Content-type', ''.join([msg.contentType,'; charset=utf-8']))
                            
            self.end_headers()
            if msg.contentType == 'image/jpeg':
                self.wfile.write(msg.body)
            else:    
                self.wfile.write(msg.body.encode('utf-8'))
      
class ResponseMsg():
    def __init__(self, code) -> None:
        self.code = code
        self.contentType = 'text/plane'
    def setBody(self, data):
        if self.contentType == 'application/json':
            self.body = json.dumps(data)
        else:
            self.body = data
    def setContentType(self, contentType):
        self.contentType = contentType
    
def getPrintersInfo(args):
    printers_requested = args.get('printer_name', None)
    try:
        conn = cups.Connection(host='localhost')
    except Exception as e:
        msg = ResponseMsg(503, 'text/html')
        msg.setBody(e.args)
        return msg
    if printers_requested == None:
        printers_data = conn.getPrinters()
    else:
        printers_data = {}
        for i in range(len(printers_requested)):
            try:
                attr = conn.getPrinterAttributes(printers_requested[i].encode('utf-8'))
                printers_data.update({printers_requested[i]:attr})
            except Exception as e:
                printers_data.update({printers_requested[i]:{'printer-state' : 0, 'printer-state-reasons' : e.args}})
    msg = ResponseMsg(200, 'application/json')
    msg.setBody(printers_data)
    return msg

def commandPrintJobs(args):
    try:
        conn = cups.Connection(host='localhost')
    except Exception as e:
        msg = ResponseMsg(503)
        msg.setBody(e.args)
        return msg 
    jobs = args.get('jobs', None)    
    jobs_data = []
    for i in range(len(jobs)):
        doc = io.BytesIO(base64.b64decode(jobs[i].get('doc')))
        printer = jobs[i].get('printer')
        name = jobs[i].get('name')
        try:
            id = conn.createJob(printer, '1C', { 'document-format':cups.CUPS_FORMAT_PDF })
            conn.startDocument(printer, id, '1C', cups.CUPS_FORMAT_PDF, 1)
            while True:
                    x = doc.read(512)
                    if len(x):
                        conn.writeRequestData(x, len(x))
                    else:
                        break
            conn.finishDocument(printer)
            jobs_data.append({'job' : name, 'printer': printer, 'printed': 1})
        except Exception as e:
                jobs_data.append({'job': name, 'printer': printer, 'printed': 0, 'desc':e.args})
    msg = ResponseMsg(200)
    msg.setContentType('application/json')
    msg.setBody(jobs_data)
    return msg

def commandPrintersStop(args):
    msg = ResponseMsg(501)
    msg.setBody('Method not implemented yet')
    return msg

def commandPrintersStart(args):
    msg = ResponseMsg(501)
    msg.setBody('Method not implemented yet')
    return msg

def commandClearJobs(args): 
    msg = ResponseMsg(501)
    msg.setBody('Method not implemented yet')
    return msg

def commandPrintersInfo(args): 
    try:
        conn = cups.Connection(host='localhost')
    except Exception as e:
        msg = ResponseMsg(503)
        msg.setBody(e.args)
        return msg
    printers_requested = args.get('printers', None)
    if printers_requested == None:
        printers_data = conn.getPrinters()
    else:
        printers_data = {}
        for i in range(len(printers_requested)):
            try:
                attr = conn.getPrinterAttributes(printers_requested[i].encode('utf-8'))
                printers_data.update({printers_requested[i]:attr})
            except Exception as e:
                printers_data.update({printers_requested[i]:{'printer-state' : 0, 'printer-state-reasons' : e.args, 'printer-state-message' : 'unknown printer'}})
    msg = ResponseMsg(200)
    msg.setContentType('application/json')
    msg.setBody(printers_data)
    return msg

def commandQueuesInfo(args): 
    msg = ResponseMsg(501)
    msg.setBody('Method not implemented yet')
    return msg

def commandRiseError(args): 
    msg = ResponseMsg(406)
    msg.setBody('Unknown command')
    return msg

def postCommandSelector(args):
    switcher = {
        'print_jobs': commandPrintJobs,
        'printers_stop': commandPrintersStop,
        'printers_start': commandPrintersStart,
        'queues_info' : commandQueuesInfo,
        'clear_queues': commandClearJobs,
        'printers_info': commandPrintersInfo
    }
    func = switcher.get(args['command'], commandRiseError)
    msg = func(args)
    return msg 
   
def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=loglevel,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
    server_address = ('', port)
    handler_class.error_content_type = 'text/plain;charset=utf-8'
    handler_class.error_message_format = '%(message)s'
    httpd = server_class(server_address, handler_class)
    logging.info('Starting 1CUPS service...')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping 1CUPS service...')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
