#!/usr/bin/python3

import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from json import JSONDecodeError, dumps, loads
from os import environ
from re import match
from socket import AF_INET6
from subprocess import STDOUT, CalledProcessError, check_output
from urllib.parse import parse_qs, urlparse

from ansi2html import Ansi2HTMLConverter


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        docker_container_names_list = container_list

        if not docker_container_names_list:

            # Built a list, because no valid container names where given as environment variables
            try:

                command = ["docker", "ps", "--all", "--format", "{{.Names}}"]

                docker_container_names_list = (
                    check_output(command, stderr=STDOUT).decode("utf-8").splitlines()
                )
                docker_container_names_list.sort()

            except CalledProcessError:

                docker_container_names_list = []
                logging.info(
                    "Could not get list of docker container names with 'docker ps --all'"
                )

        parsed = urlparse(self.path)

        path = parsed.path.strip("/")
        path_parts = path.split("/")

        path_command_part = None
        try:
            path_command_part = "/".join(path_parts[0:-1])
        except IndexError:
            pass

        path_container_part = None
        try:
            path_container_part = path_parts[-1]
        except IndexError:
            pass

        query = parse_qs(parsed.query)

        accept_header = ""
        try:
            accept_header = self.headers.get("Accept")
            accept_header = accept_header.split(",", 1)[0]
        except AttributeError:
            pass

        if not path_command_part and not path_container_part:

            if accept_header == "text/html":

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                output = """<!DOCTYPE html>
<html>
     <head>
         <title>Docker Logs Looker</title>
         <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
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
"""

                output = add_refresh_meta_tag_if_necessary(output, query)

                for container in docker_container_names_list:

                    output += f'<a href="/command/logs/{container}">{container}</a>'

                    if inspect_environ:

                        output += f' <a href="/command/inspect/{container}">ℹ️</a>'

                    if health_environ:

                        output += f' <a href="/health/{container}">🏥</a>'

                    output += "\n"

                output += """        </pre>
    </body>
</html>
"""

                self.wfile.write(output.encode("utf-8"))

                return

            # Fallback to "text/plain"

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()

            output = ""

            for container in docker_container_names_list:

                output += f"{container}\n"

            self.wfile.write(output.encode("utf-8"))

            return

        if path_command_part == "command/logs" and path_container_part:

            for container in docker_container_names_list:

                if path_container_part == container:

                    tail = tail_environ
                    try:

                        tail = query["tail"][0]
                        tail = int(tail)
                        tail = abs(tail)

                    except (KeyError, ValueError):

                        pass

                    timestamps = timestamps_environ
                    try:

                        map_default = timestamps

                        timestamps = query["timestamps"][0]
                        timestamps = timestamps.lower()
                        timestamps = map_boolean.get(timestamps, map_default)

                    except KeyError:

                        pass

                    output = None
                    try:

                        command = ["docker", "logs", "--tail", str(tail)]
                        if timestamps:
                            command.append("--timestamps")
                        command.append(str(container))

                        output = check_output(command, stderr=STDOUT)

                        if accept_header == "text/html":

                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()

                            output = convert_to_html(
                                output, f"{container} - Docker Logs Looker"
                            )

                            output = add_refresh_meta_tag_if_necessary(output, query)

                            self.wfile.write(output)

                            return

                        # Fallback to "text/plain"

                        self.send_response(200)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()

                        self.wfile.write(output)

                        return

                    except CalledProcessError:

                        self.send_response(404)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()

                        self.wfile.write(
                            f"Could not get logs for '{container}'".encode("utf-8")
                        )

                        return

                    return

        if (
            inspect_environ
            and path_command_part == "command/inspect"
            and path_container_part
        ):

            for container in docker_container_names_list:

                if path_container_part == container:

                    output = None
                    try:

                        command = [
                            "docker",
                            "inspect",
                            "--format",
                            "json",
                            str(container),
                        ]

                        output = check_output(command, stderr=STDOUT)

                        # Pretty printing JSON. Also validates that output is really JSON
                        output = loads(output)
                        output = dumps(output, indent=4).encode("utf-8")

                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()

                        self.wfile.write(output)

                    except (CalledProcessError, JSONDecodeError):

                        self.send_response(404)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()

                        self.wfile.write(
                            f"Could not inspect '{container}'".encode("utf-8")
                        )

                    return

        if health_environ and path_command_part == "health" and path_container_part:

            for container in docker_container_names_list:

                if path_container_part == container:

                    output = None
                    try:

                        command = [
                            "docker",
                            "inspect",
                            "--format",
                            "{{ .State.Health.Status }}",
                            str(container),
                        ]

                        output = check_output(command, stderr=STDOUT)
                        output = output.strip()

                        if accept_header == "text/html":

                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()

                            output = convert_to_html(
                                output, f"{container} - Docker Logs Looker"
                            )

                            output = add_refresh_meta_tag_if_necessary(output, query)

                            self.wfile.write(output)

                            return

                        # Fallback to "text/plain"

                        self.send_response(200)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()

                        self.wfile.write(output)

                        return

                    except (CalledProcessError, JSONDecodeError):

                        self.send_response(404)
                        self.send_header("Content-type", "text/plain")
                        self.end_headers()

                        self.wfile.write(
                            f"Could not get health of '{container}'".encode("utf-8")
                        )

                    return

        self.send_response(404)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        self.wfile.write(f"'{path}' not found".encode("utf-8"))


map_boolean = {
    "": True,
    "true": True,
    "1": True,
    "yes": True,
    "y": True,
    "enable": True,
    "on": True,
    "false": False,
    "0": False,
    "no": False,
    "n": False,
    "disable": False,
    "off": False,
}

ansi_converter = Ansi2HTMLConverter()


def convert_to_html(ansi_text, html_title=""):
    output = ansi_converter.convert(ansi_text.decode())
    output = output.replace(
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">',
        "<!DOCTYPE html>",
        1,
    )
    if html_title:
        output = output.replace("<title>", f"<title>{html_title}", 1)
    output = output.replace(
        '<pre class="ansi2html-content">\n', '<pre class="ansi2html-content">', 1
    )
    output = output.replace("\n</pre>", "</pre>", 1)
    output = output.replace("</body>\n", "</body>", 1)
    output = output.encode("utf-8")
    return output


def add_refresh_meta_tag_if_necessary(html, query):

    output = html
    is_string = isinstance(output, str)
    try:

        refresh_seconds = query["refresh"][0]
        logging.info(refresh_seconds)
        refresh_seconds = int(refresh_seconds)

        if refresh_seconds > 0:
            if not is_string:
                output = output.decode()
            output = output.replace(
                "</title>\n",
                f'</title>\n<meta http-equiv="refresh" content="{refresh_seconds}">\n',
                1,
            )
            if not is_string:
                output = output.encode("utf-8")

    except (KeyError, ValueError):

        pass
    return output


logging.basicConfig(format="%(message)s", level=logging.INFO)

container_list = None
try:

    container_list = list()

    for container_name in environ["CONTAINER_LIST"].split(","):

        if match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]+$", container_name):

            container_list.append(container_name)

        else:

            logging.info(
                f"'📦 {container_name}' is not a valid container name. Skipping"
            )

except KeyError:

    pass

if container_list:

    container_list.sort()
    logging.info(f"📦 These containers logs are available: {', '.join(container_list)}")

else:

    logging.info(
        "📦 Since no 'CONTAINER_LIST' environment variable was given ALL containers logs will be available"
    )

tail_environ = 100
try:

    tail_environ = environ["TAIL"]
    tail_environ = int(tail_environ)
    tail_environ = abs(tail_environ)

except (KeyError, ValueError):

    pass

logging.info(f"📝 Default log tail will be {tail_environ} lines")

timestamps_environ = False
try:

    map_default = timestamps_environ

    timestamps_environ = environ["TIMESTAMPS"]
    timestamps_environ = timestamps_environ.lower()
    timestamps_environ = map_boolean.get(timestamps_environ, map_default)

except KeyError:

    pass

if timestamps_environ:
    logging.info("📅 Timestamps will be shown by default")
else:
    logging.info("📅 Timestamps will NOT be shown by default")

inspect_environ = False
try:

    map_default = inspect_environ

    inspect_environ = environ["INSPECT"]
    inspect_environ = inspect_environ.lower()
    inspect_environ = map_boolean.get(inspect_environ, map_default)

except KeyError:

    pass

if inspect_environ:
    logging.info("ℹ️ The 'inspect' command is available")
else:
    logging.info("ℹ️ The 'inspect' command is NOT available")

health_environ = False
try:

    map_default = health_environ

    health_environ = environ["HEALTH"]
    health_environ = health_environ.lower()
    health_environ = map_boolean.get(health_environ, map_default)

except KeyError:

    pass

if health_environ:
    logging.info("🏥 Container 'health' is available")
else:
    logging.info("🏥 Container 'health' is NOT available")


class HTTPServerV6(HTTPServer):
    address_family = AF_INET6


httpd = HTTPServerV6(("::", 8080), SimpleHTTPRequestHandler)
try:

    logging.info("🟢 Docker Logs Looker started")
    httpd.serve_forever()

except KeyboardInterrupt:

    pass

finally:

    logging.info("\n🔴 Docker Logs Looker stopped")
    httpd.server_close()
