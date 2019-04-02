"""
Malware Analysis Detection Laboratory

This server scan job order and run it on our cluster (21 nodes, 16TB)

Stay tuned with the mailing list : madlab@inria.fr
"""
import datetime
import inspect
import logging
import sys
import threading
import time
import traceback

import docker

import conf
import madlab
import wrapper

from pymongo import MongoClient

client = MongoClient(conf.mongourl)

dockers = {h: {'docker': docker.DockerClient(base_url=h, version=conf.docker_api_version),
               'api': docker.APIClient(base_url=h, version=conf.docker_api_version),
               'model': m}
           for h, m in conf.docker_hosts.items()}

logging.getLogger("requests").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('madlab')


class Job(madlab.Job):

    def parse_logs(self, c):
        stdout = c.logs(stdout=True, stderr=False)
        for l in stdout.decode('utf8').split('\n'):
            log.debug("job id stdout %s - %s", self._id, l)
            self.stdout.append(l)

        stderr = c.logs(stdout=False, stderr=True)
        for l in stderr.decode('utf8').split('\n'):
            log.debug("job id stderr %s - %s", self._id, l)
            self.stderr.append(l)
            self.save()

    def run(self, c):
        while c and c.status in ["running", "created"]:
            self.status(c.status)
            time.sleep(1)
            c.reload()
        self.status(c.status)
        self.parse_logs(c)
        c.remove()

    def save(self):
        d = self.__dict__.copy()
        del d['container']
        log.debug(d)
        client.madlab.jobs.replace_one({'_id': self._id}, d)

    def set_result(self, data):
        self.result = data
        self.save()

    def load(self):
        data = client.madlab.jobs.find_one({'_id': self._id})
        self.__dict__.update(data)


def worker(j, host, model):
    log.info("Thread start : %s", j)
    for name, obj in inspect.getmembers(sys.modules["wrapper"]):
        if name != 'Job' and name == j.app and inspect.isclass(obj):
            log.info("Run %s %s", name, obj)
            try:
                obj(j).run(host, model)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                j.stderr.append(str(e))
                j.status("error")
    log.info("Thread stop : %s", j)


def app_limit(j):
    for name, obj in inspect.getmembers(sys.modules["wrapper"]):
        if name != 'Job' and name == j.app and inspect.isclass(obj):
            return obj(j).threads, obj(j).memory_in_gb


def host_fit(j):
    threads_needed, memory_needed = app_limit(j)
    for d in dockers.values():
        api = d['api']
        m = d['model']
        cpu_needed = threads_needed * 10 ** 9 / m['threads'] if threads_needed else 10 ** 9
        memory_needed = memory_needed * 10 ** 9 if memory_needed else m['memory_in_gb'] * 10 ** 9
        mem_used = sum([api.inspect_container(c)['HostConfig']['Memory'] for c in api.containers()])
        cpu_used = sum([api.inspect_container(c)['HostConfig']['NanoCpus'] for c in api.containers()])
        mem_avai = m['memory_in_gb'] * 10 ** 9 - mem_used
        cpu_avai = 10 ** 9 - cpu_used
        log.debug("best fit called for job %s:%s : %03d %03d - available %03d %03d",
                  j.app, j._id, memory_needed, threads_needed, mem_avai, cpu_avai)
        if mem_avai >= memory_needed and cpu_avai >= cpu_needed:
            return d['docker'], d['model']
    return None, None


def main():
    threads = {}
    while True:
        for r in client.madlab.jobs.find({'current_status': None}):
            id_ = r['_id']
            j = Job(id_)
            log.debug("Job to launch %s", j)
            host, model = host_fit(j)
            if host and model:
                j.status('init')
                t = threading.Thread(target=worker, args=(j, host, model))
                threads[id_] = t
                t.start()
            # if len(threads) > conf.max_threads:
            # time.sleep(5)
        print('Wait ...')
        time.sleep(5)


if __name__ == '__main__':
    main()
