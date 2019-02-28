import inspect
import logging
import sys
import threading
import time

import docker
import conf
import madlab

from pymongo import MongoClient

client = MongoClient(conf.mongourl)

dockers = [docker.DockerClient(base_url=h) for h in conf.docker_hosts]
logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('madlab')


class Job(madlab.Job):

    def parse_logs(self, logs):
        print(logs)
        for l in logs.decode('utf8').split('\n'):
            log.debug("job id %s - %s", self._id, l)
            self.logs.append(l)
            self.save()

    def run(self, c):
        self.container = c
        while c.status in ["running", "created"]:
            self.status(c.status)
            time.sleep(1)
            c.reload()
        self.status(c.status)
        self.parse_logs(c.logs())

    def save(self):
        d = self.__dict__.copy()
        del d['container']
        client.madlab.jobs.replace_one({'_id': self._id}, d)

    def set_result(self, data):
        self.result = data
        self.save()

    def load(self):
        data = client.madlab.jobs.find_one({'_id': self._id})
        self.__dict__.update(data)


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
        job.set_result("My results")


class SCDG_Extraction(AbstractWorker):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/scdg/trace_gridfs"
    volumes = {'/scratch': {'bind': '/scratch', 'mode': 'rw'},
               '/database': {'bind': '/database', 'mode': 'ro'}}

    def get_cmd(self, params):
        return "python trace_calls.py /code/tests/binaries/pe/32/helloword.exe"

    def set_result(self, job):
        job.set_result("My results")


def worker(j):
    log.info("Thread start : %s", j)
    for name, obj in inspect.getmembers(sys.modules[__name__]):

        if name != 'Job' and name == j.app and inspect.isclass(obj):
            log.info("Run %s %s", name, obj)
            obj(j).run(dockers[0])
    log.info("Thread stop : %s", j)


if __name__ == '__main__':
    threads = []
    while True:
        for r in client.madlab.jobs.find({'current_status': None}):
            j = Job(r['_id'])
            j.status('init')
            t = threading.Thread(target=worker, args=(j,))
            threads.append(t)
            t.start()
        if len(threads) > conf.max_threads:
            time.sleep(5)
