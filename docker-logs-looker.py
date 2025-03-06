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

            # Built a list, because no valid container names where given as environment variables
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

            if self.headers.get('Accept').split(',', 1)[0] == 'text/html':

                self.send_header('Content-type', 'text/html')
                self.end_headers()

                output = '''<!doctype html>
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

                    output += f'<a href="/{container}">{container}</a>\n'

                output += '''        </pre>
    </body>
</html>
'''

            else:

                self.send_header('Content-type', 'text/plain')
                self.end_headers()

                output = ''

                for container in docker_container_names_list:

                    output += f'{container}\n'

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

                        output = check_output(['docker', 'logs', '--tail', str(tail), '-t', str(container)], stderr=STDOUT)
                        self.send_response(200)

                        if self.headers.get('Accept').split(',', 1)[0] == 'text/html':

                            self.send_header('Content-type', 'text/html')
                            output = ansi_converter.convert(output.decode())
                            output = output.replace('<title>', f'<title>{container} - ')
                            output = output.encode('utf-8')

                        else:

                            self.send_header('Content-type', 'text/plain')

                        self.end_headers()

                        self.wfile.write(output)

                    except CalledProcessError:

                        self.send_response(404)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()

                        self.wfile.write(f'Could not get logs for "{container}"'.encode('utf-8'))

                    found = True

                    break

            if not found:

                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()

                self.wfile.write(f'"{path}" not found'.encode('utf-8'))


logging.basicConfig(format='%(message)s', level=logging.INFO)

container_list = None
try:

    container_list = list()

    for container_name in environ['CONTAINER_LIST'].split(','):

        if (match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]+$', container_name)):

            container_list.append(container_name)

        else:

            logging.info(f'"{container_name}" is not a valid container name. Skipping')

except KeyError:

    pass

if container_list:

    container_list.sort()
    logging.info(f'These containers logs are available: {", ".join(container_list)}')

else:

    logging.info('Since no "CONTAINER_LIST" environment variable was given ALL containers logs will be available')

tail_environ = 100
try:

    tail_environ = abs(int(environ['TAIL']))

except (KeyError, ValueError):

    pass

logging.info(f'Default log tail will be {tail_environ} lines')

ansi_converter = Ansi2HTMLConverter(title="Docker Logs Looker")

httpd = HTTPServer(('', 8080), SimpleHTTPRequestHandler)
try:

    logging.info('Docker Logs Looker started')
    httpd.serve_forever()

except KeyboardInterrupt:

    pass

finally:

    logging.info('\nDocker Logs Looker stopped')
    httpd.server_close()
