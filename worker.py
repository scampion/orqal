import logging
import time
from multiprocessing import Process

import docker
import conf

from madlab import Job

dockers = [docker.DockerClient(base_url=h) for h in conf.docker_hosts]


class Test:
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def __init__(self, job):
        self.log = logging.getLogger(str(self.__class__))
        self.job = job

    def run(self, client, tag='latest'):
        image = self.docker_url + ':' + tag
        self.log.debug("Pull image %s", self.docker_url)
        client.images.pull(self.docker_url, tag, auth_config=conf.auth_config)
        print(self.job.__dict__)
        cmd = "python3 simple_job.py %s %s %s" % (self.job.params['app']['echo'], self.job.params['app']['time'],
                                                  self.job.params['app']['exit_code'])
        c = client.containers.run(image, cmd, detach=True, auto_remove=False, stream=True)
        self.job.status("running")

        p = Process(target=self.job.logs, args=(c, ))
        p.start()
        time.sleep(1)
        self.log.debug("status %s", c.status)
        while c.status in ["running", "created"]:
            self.log.debug("Jobid %s is running %s", self.job.id, c.status)
            time.sleep(1)
            c.reload()
        self.log.debug("status %s", c.status)

        p.terminate()


if __name__ == '__main__':
    input = None
    params = {"app": {'echo': 'test', 'time': 10, 'exit_code': 2}}
    j = Job(0, input, params)
    Test(j).run(dockers[0])
