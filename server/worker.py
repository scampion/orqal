import logging
import time
from multiprocessing import Process

import docker
import conf

from madlab import Job

dockers = [docker.DockerClient(base_url=h) for h in conf.docker_hosts]


def postlogs(job, container):
    job.logs(container.logs())


class Test:
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def __init__(self, job):
        self.log = logging.getLogger(str(self.__class__))
        self.job = job

    def run(self, client, tag='latest'):
        image = self.docker_url + ':' + tag
        self.log.debug("Pull image %s", self.docker_url)
        client.images.pull(self.docker_url, tag, auth_config=conf.auth_config)
        c = client.containers.run(image, "python3 simple_job.py 2 10 2", detach=True, auto_remove=True, stream=True)
        self.job.status("running")

        p = Process(target=postlogs, args=(job, c))
        p.start()
        time.sleep(1)
        self.log.debug("status %s", c.status)
        while c.status in ["running", "created"]:
            self.log.info("Jobid %s is running %s", self.job.id, c.status)
            time.sleep(1)
            c.reload()
        self.log.debug("status %s", c.status)

        p.terminate()


if __name__ == '__main__':
    j = Job(0, None, None)
    Test(j).run(dockers[0])
