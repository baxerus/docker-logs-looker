[![Docker](https://github.com/baxerus/docker-logs-looker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/baxerus/docker-logs-looker/actions/workflows/docker-publish.yml)

# docker-logs-looker

Look at docker logs with your browser (or general via HTTP)

This is basically a very shallow wrapper around the `docker logs` command. It should enable you to use your browser to fastly check if everything with your **hand crafted and started** docker containers is okay (sometimes SSHing into you machine and running commands there is simply cumbersome).  
If your docker containers are not **hand crafted and started** and you are using something more fancy to start and control you containers (like e.g. [portainer.io](https://www.portainer.io/) or similar), then this tool will give you better possiblities to do similar stuff like this container anyway.

## Usage:
The `docker-compose.yml` shows a **very basic** usage example.  
Of course I would **highly encourage** to use some sort of **authorization mechanisim** in front of this container.
