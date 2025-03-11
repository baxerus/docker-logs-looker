#!/usr/bin/python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from os import environ
from subprocess import check_output, STDOUT, CalledProcessError
from urllib.parse import urlparse, parse_qs
from re import match
import logging
from ansi2html import Ansi2HTMLConverter
from json import loads, dumps, JSONDecodeError


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        docker_container_names_list = container_list

        if not docker_container_names_list:

            # Built a list, because no valid container names where given as environment variables
            try:

                command = ['docker', 'ps', '--all', '--format', '{{.Names}}']

                docker_container_names_list = check_output(command, stderr=STDOUT).decode('utf-8').splitlines()
                docker_container_names_list.sort()

            except CalledProcessError:

                docker_container_names_list = []
                logging.info('Could not get list of docker container names with "docker ps --all"')

        parsed = urlparse(self.path)

        path = parsed.path.strip('/')
        path_parts = path.split('/')

        path_command_part = None
        try:
            path_command_part = path_parts[0]
        except IndexError:
            pass

        path_container_part = None
        try:
            path_container_part = path_parts[1]
        except IndexError:
            pass

        query = parse_qs(parsed.query)

        if not path_command_part:

            self.send_response(200)

            if self.headers.get('Accept').split(',', 1)[0] == 'text/html':

                self.send_header('Content-type', 'text/html')
                self.end_headers()

                output = '''<!doctype html>
<html>
     <head>
         <title>Docker Logs Looker</title>
         <meta charset="UTF-8">
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

                    output += f'<a href="/logs/{container}">{container}</a>'

                    if inspect_environ:

                        output += f' <a href="/inspect/{container}">ℹ️</a>'

                    output += '\n'

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

            return

        if path_command_part == 'logs' and path_container_part:

            for container in docker_container_names_list:

                if path_container_part == container:

                    tail = tail_environ
                    try:

                        tail = abs(int(query['tail'][0]))

                    except (KeyError, ValueError):

                        pass

                    timestamps = timestamps_environ
                    try:

                        timestamps = map_boolean.get(query['timestamps'][0].lower(), timestamps)

                    except KeyError:

                        pass

                    output = None
                    try:

                        command = ['docker', 'logs', '--tail', str(tail)]
                        if timestamps:
                            command.append('--timestamps')
                        command.append(str(container))

                        output = check_output(command, stderr=STDOUT)

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

                        self.wfile.write(
                            f'Could not get logs for "{container}"'.encode('utf-8')
                        )

                    return

        if inspect_environ and path_command_part == 'inspect' and path_container_part:

            for container in docker_container_names_list:

                if path_container_part == container:

                    output = None
                    try:

                        command = ['docker', 'inspect', '--format', 'json', str(container)]

                        output = check_output(command, stderr=STDOUT)

                        # Pretty printing JSON. Also validates that output is really JSON
                        output = loads(output)
                        output = dumps(output, indent=4).encode('utf-8')

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()

                        self.wfile.write(output)

                    except (CalledProcessError, JSONDecodeError):

                        self.send_response(404)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()

                        self.wfile.write(
                            f'Could not inspect "{container}"'.encode('utf-8')
                        )

                    return

        self.send_response(404)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        self.wfile.write(f'"{path}" not found'.encode('utf-8'))


map_boolean = {
    '': True,
    'true': True,
    '1': True,
    'yes': True,
    'y': True,
    'enable': True,
    'on': True,
    'false': False,
    '0': False,
    'no': False,
    'n': False,
    'disable': False,
    'off': False
    }

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

timestamps_environ = False
try:

    timestamps_environ = map_boolean.get(environ['TIMESTAMPS'].lower(), timestamps_environ)

except KeyError:

    pass

if timestamps_environ:
    logging.info('Timestamps will be shown by default')
else:
    logging.info('Timestamps will NOT be shown by default')

inspect_environ = False
try:

    inspect_environ = map_boolean.get(environ['INSPECT'].lower(), timestamps_environ)

except KeyError:

    pass

if inspect_environ:
    logging.info('The "inspect" command is available')
else:
    logging.info('The "inspect" command is NOT available')

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
