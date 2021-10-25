#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import logging
import cups
import base64
import urllib.parse as urlparse
import markdown

class S(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args):
        logging.info('Request: {0}'.format(args))
    def _set_response(self, http_code, content_type):
        self.send_response(http_code)
        self.send_header('Content-type', ''.join([content_type,'; charset=utf-8']))
        self.end_headers()
    
    def do_GET(self):        
        if self.path == '/favicon.ico':
            self._set_response(200, 'image/jpeg')
            with open("favicon.ico", "rb") as fout:
                self.wfile.write(fout.read())
            return
        parsed_path = urlparse.urlparse(self.path)
        queryParams = urlparse.parse_qs(parsed_path.query)
        logging.debug(queryParams)
        data = commandSelector(queryParams)
        self._set_response(200, 'text/html')
        logging.debug(data)
        self.wfile.write(bytes(data.encode('utf-8')))                
                
    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself

        with io.BytesIO(base64.b64decode(post_data)) as f:
                parsed_path = urlparse.urlparse(self.path)
                queryParams = urlparse.parse_qs(parsed_path.query)
                keys = queryParams.keys()
                if 'printer_name' not in keys:
                    self._set_response(400)
                    self.wfile.write('Printer not specified'.format(content_length).encode('utf-8'))
                    return
                conn = cups.Connection(host='localhost')
                try:
                    id = conn.createJob(queryParams['printer_name'][0], '1C', { 'document-format':cups.CUPS_FORMAT_PDF })
                    conn.startDocument(queryParams['printer_name'][0], id, '1C', cups.CUPS_FORMAT_PDF, 1)
                    while True:
                        x = f.read(512)
                        if len(x):
                            conn.writeRequestData(x, len(x))
                        else:
                            break
                    conn.finishDocument(queryParams['printer_name'][0])
                except Exception as e:
                    self._set_response(400, 'application/json')
                    self.wfile.write('Document print error: {0}'.format(e).encode('utf-8'))
                    return
        self._set_response(200,'application/json')
        self.wfile.write('Print document succesfully'.format(content_length).encode('utf-8'))

def getHelpPage(args):
    text = ''
    with open("README.md", "r", encoding="utf-8") as input_file:
        text = input_file.read()
    return markdown.markdown(text, output_format='html')
    
def getPrinterStatus(args):
    conn = cups.Connection(host='localhost')
    printer_name = args.get('printer_name', None)
    if printer_name == None:
        logging.debug('printer_name parameter is required')
        return ''
    if len(printer_name) == 1:
        attr = conn.getPrinterAttributes(printer_name[0].encode('utf-8'))
    else:
        logging.critical('Too many "printer_name" parameters')
        attr = getHelpPage(args)
    return attr

def commandSelector(args):
    switcher = {
        'get_printer_status': getPrinterStatus,
        'get_help_page': getHelpPage
    }
        
    command = args.get('command', 'get_help_page')
    if len(command) == 1:
        func = switcher.get(str(command[0]), getHelpPage)
        data = func(args)
    else:
        logging.critical('Too many "command" parameters')
        data = getHelpPage(args)
    return data 
    
def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting print service...')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping print service...')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
