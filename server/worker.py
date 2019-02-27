import docker

import conf

dockers = [docker.DockerClient(base_url=h) for h in conf.docker_hosts]


class App:
    docker_url = None

    def __init__(self):
        for d in dockers:
            d.images.pull(self.docker_url)

