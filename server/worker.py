import docker

import conf

dockers = [docker.client.Client(base_url=h) for h in conf.docker_hosts]


class Test:
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def __init__(self, id, client, tag='latest'):
        import ipdb;
        ipdb.set_trace()
        client.images.pull(self.docker_url + ':' + tag)
        client.run()


if __name__ == '__main__':
    Test(0, dockers[0])
