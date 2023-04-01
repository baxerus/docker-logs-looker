#!/usr/bin/python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from os import environ
from subprocess import check_output, STDOUT, CalledProcessError
from urllib.parse import urlparse, parse_qs
from re import match
import logging
from ansi2html import Ansi2HTMLConverter


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        docker_container_names_list = container_list

        if not docker_container_names_list:
            # Built a list, because no valid container names where given as enviroment variables
            try:
                docker_container_names_list = check_output(['docker', 'ps', '--all', '--format', '{{.Names}}'], stderr=STDOUT).decode('utf-8').splitlines()
                docker_container_names_list.sort()
            except CalledProcessError:
                docker_container_names_list = []
                logging.info('Could not get list of docker container names with "docker ps --all"')

        parsed = urlparse(self.path)
        path = parsed.path.split('/')[-1]
        query = parse_qs(parsed.query)

        if path == '':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            output =  '''<!doctype html>
<html>
     <head>
         <title>Docker Logs Looker</title>
         <style type="text/css">
             body {
                 background-color: #000000;
             }
             a:link {
                 color: #bbbbbb;
                 text-decoration: none;
             }
             a:visited {
                 color: #888888;
             }
             a:hover, a:active {
                 text-decoration: underline;
             }
         </style>
     </head>
     <body>
         <pre>
'''
            for container in docker_container_names_list:
                output += '<a href="/{}">{}</a>\n'.format(container, container)
            output += '''        </pre>
    </body>
</html>
'''
            self.wfile.write(output.encode('utf-8'))

        else:
            found = False
            for container in docker_container_names_list:
                if path == container:

                    tail = tail_environ
                    try:
                        tail = abs(int(query['tail'][0]))
                    except (KeyError, ValueError):
                        pass

                    output = None
                    try:
                        output = check_output(['docker', 'logs', '--tail', '{}'.format(tail), '-t', '{}'.format(container)], stderr=STDOUT)
                    except CalledProcessError:
                        pass

                    if output:
                        self.send_response(200)
                        if self.headers.get('accept').split(',', 1)[0] == 'text/html':
                            self.send_header('Content-type', 'text/html')                        
                            output = ansi_converter.convert(output.decode()).encode('utf-8')
                        else:
                            self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(output)

                    else:
                        self.send_response(404)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write('Could not get logs for "{}"'.format(container).encode('utf-8'))

                    found = True
                    break

            if not found:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('"{}" not found'.format(path).encode('utf-8'))


logging.basicConfig(format='%(message)s', level=logging.INFO)

container_list = None
try:
    container_list = list()
    for container_name in environ['CONTAINER_LIST'].split(','):
        if (match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]+$', container_name)):
            container_list.append(container_name)
        else:
            logging.info('"{}" is not a valid container name. Skipping'.format(container_name))
except KeyError:
    pass

if container_list:
    container_list.sort()
    logging.info('These containers logs are available: {}'.format(', '.join(container_list)))
else:
    logging.info('Since no "CONTAINER_LIST" enviroment variable was given ALL containers logs will be available')

tail_environ = 100
try:
    tail_environ = abs(int(environ['TAIL']))
except (KeyError, ValueError):
    pass
logging.info('Default log tail will be {} lines'.format(tail_environ))

ansi_converter = Ansi2HTMLConverter()
ansi_converter.convert('test')

httpd = HTTPServer(('', 8080), SimpleHTTPRequestHandler)
try:
    logging.info('Docker Logs Looker started')
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    logging.info('\nDocker Logs Looker stopped')
    httpd.server_close()
