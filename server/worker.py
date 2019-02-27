import logging
import docker
import conf

dockers = [docker.DockerClient(base_url=h) for h in conf.docker_hosts]


class Test:
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def __init__(self, id, input, params, client, tag='latest'):
        self.log = logging.getLogger(self.__class__)
        self.log.debug("Pull image %s", self.docker_url)
        client.images.pull(self.docker_url, tag, auth_config=conf.auth_config)
        client.run()


if __name__ == '__main__':
    Test(0, None, None, dockers[0])
