#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ast import Raise
from distutils import command
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import inspect, os.path
import logging
import cups
import base64
import markdown
import json
import jsonschema

filename = inspect.getframeinfo(inspect.currentframe()).filename
file_path = os.path.dirname(os.path.abspath(filename))
json_schema = json.loads(open(""+file_path+"/schema.json", "r").read())
fout = open(""+file_path+"/favicon.ico", "rb").read()
text_help = open(""+file_path+"/README.md", "r", encoding="utf-8").read()
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
            self.send_error(msg.code, str(msg.body))
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
        ext_id = jobs[i].get('id')
        try:
            id = conn.createJob(printer, name, { 'document-format':cups.CUPS_FORMAT_PDF })
            conn.startDocument(printer, id, name, cups.CUPS_FORMAT_PDF, 1)
            while True:
                    x = doc.read(512)
                    if len(x):
                        conn.writeRequestData(x, len(x))
                    else:
                        break
            conn.finishDocument(printer)
            jobs_data.append({'id':ext_id, 'data':{'job':name, 'printer':printer, 'printer-state':1, 'job-id':id, 'printer-state-message':'job accepted'}})
        except Exception as e:
            jobs_data.append({'id':ext_id, 'data':{'job':name, 'printer':printer, 'printer-state':0, 'printer-state-message':'job rejected', 'printer-state-reasons':e.args}})
    msg = ResponseMsg(200)
    msg.setContentType('application/json')
    msg.setBody(jobs_data)
    return msg

def commandServiceCommand(args): 
    try:
        conn = cups.Connection(host='localhost')
    except Exception as e:
        msg = ResponseMsg(503)
        msg.setBody(e.args)
        return msg
    printers_requested = args.get('printers', None)
    printers_data = []
    if args['command'] == 'printers_info' and printers_requested == None:
#TODO Возвращать массив данных?      
        printers_data = conn.getPrinters()
    else:
        for i in range(len(printers_requested)):
            printer = printers_requested[i].get('printer')
            ext_id = printers_requested[i].get('id')
            try:
                switcher = {
                'printers_info' : conn.getPrinterAttributes,
                'print_test_page' : conn.printTestPage,
                'printers_disable' : conn.disablePrinter,
                'printers_enable' : conn.enablePrinter
                }
                func = switcher.get(args['command'], commandRiseError)
                attr = func(printer.encode('utf-8'))
                if args['command'] == 'printers_info':
                    printers_data.append({'id':ext_id, 'data':attr})
                elif args['command'] == 'print_test_page':
                    printers_data.append({'id':ext_id, 'data':{'printer-state':1, 'job-id':attr, 'printer-state-message':'job accepted'}})    
            except Exception as e:
                printers_data.append({'id':ext_id, 'data':{'printer-state':0, 'printer-state-reasons':e.args, 'printer-state-message':'unknown printer'}})
    msg = ResponseMsg(200)
    msg.setContentType('application/json')
    msg.setBody(printers_data)
    return msg

def commandRiseError(args): 
    msg = ResponseMsg(406)
    msg.setBody('unknown command')
    return msg

def postCommandSelector(args):
    switcher = {
        'print_jobs': commandPrintJobs,
        'printers_disable': commandServiceCommand,
        'printers_enable': commandServiceCommand,
        'print_test_page': commandServiceCommand,
        'printers_info': commandServiceCommand
    }
    func = switcher.get(args['command'], commandRiseError)
    msg = func(args)
    return msg 
   
def start(server_class=HTTPServer, handler_class=S, port=8080):
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
    start()