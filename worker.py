import logging
import time
from multiprocessing import Process

import docker
import conf

from madlab import Job

dockers = [docker.DockerClient(base_url=h) for h in conf.docker_hosts]

logging.basicConfig(level=logging.DEBUG)


class AbstractWorker:
    docker_url = None
    volumes = None

    def __init__(self, job):
        self.log = logging.getLogger(str(self.__class__))
        self.job = job

    def run(self, client, tag='latest'):
        self.log.debug("Pull image %s", self.docker_url)
        client.images.pull(self.docker_url, tag, auth_config=conf.auth_config)

        self.job.run(client.containers.run(self.docker_url + ':' + tag,
                                           self.get_cmd(self.job.params['app']),
                                           volumes=self.volumes,
                                           detach=True, auto_remove=conf.auto_remove))
        self.set_result(self.job)


class Test(AbstractWorker):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def get_cmd(self, params):
        return "python3 simple_job.py %s %s %s" % (params['echo'], params['time'], params['exit_code'])

    def set_result(self, job):
        job.result("My results")


class SCDG_Extraction(AbstractWorker):
    """
    Wrapper for SCDG Extraction
    """
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/scdg/trace_gridfs"
    volumes = {'/scratch': {'bind': '/scratch', 'mode': 'rw'},
               '/database': {'bind': '/database', 'mode': 'ro'}}

    def get_cmd(self, params):
        return "python trace_calls.py /code/tests/binaries/pe/32/helloword.exe"

    def set_result(self, job):
        job.result("My results")


if __name__ == '__main__':
    input = None
    params = {"app": {'echo': 'test', 'time': 10, 'exit_code': 2}}
    params = {"app": {}}
    j = Job(0, input, params)
    SCDG_Extraction(j).run(dockers[0])
