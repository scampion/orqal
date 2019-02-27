import docker

import conf

token = "65sX2-9sSXSp-hs-XeZ8"
dockers = [docker.client.Client(base_url=h) for h in conf.docker_hosts]


class App:
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def __init__(self):
        for d in dockers:
            d.images.pull(self.docker_url)


if __name__ == '__main__':
    App()
