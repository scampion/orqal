import inspect
import json
import logging
import os
import random
import sys
import threading
import time
import traceback

import docker

import conf
import orqal
import wrapper

from pymongo import MongoClient

client = MongoClient(conf.mongourl)

dockers = {h: {'docker': docker.DockerClient(base_url=h, version=conf.docker_api_version),
               'api': docker.APIClient(base_url=h, version=conf.docker_api_version)}
           for h in conf.docker_hosts}

logging.getLogger("requests").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('orqal:worker')


class Job(orqal.Job):

    def __init__(self, id=None, app=None, input=None, params={}, start=False):
        super().__init__(id, app, input, params, start)
        self.wd = os.path.join(conf.jobs_dir, str(self._id))
        self.inspect = None
        self.container_id = None

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

    def run(self, api, c):
        self.container_id = c.id
        self.save()
        try:
            while c and c.status in ["running", "created"]:
                self.status(c.status)
                time.sleep(10)
                c.reload()
            self.status(c.status)
            self.parse_logs(c)
        except Exception as e:
            log.error(e)
            self.status("error")
        finally:
            self.inspect = api.inspect_container(c.id)
            self.save()
            logging.debug("inspect results : %s", self.inspect)
            c.remove()

    def save(self):
        d = self.__dict__.copy()
        del d['container']
        client.orqal.jobs.replace_one({'_id': self._id}, d)

    def set_result(self, data):
        self.result = data
        self.save()

    def load(self):
        data = client.orqal.jobs.find_one({'_id': self._id})
        self.__dict__.update(data)


def worker(j, d):
    log.info("Thread start : %s", j)
    for name, obj in inspect.getmembers(sys.modules["wrapper"]):
        if name != 'Job' and name == j.app and inspect.isclass(obj):
            log.info("Run %s %s", name, obj)
            try:
                obj(j).run(d)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                j.stderr.append(str(e))
                j.status("error")
    log.info("Thread stop : %s", j)


def app_limit(j):
    for name, obj in inspect.getmembers(sys.modules["wrapper"]):
        if name != 'Job' and name == j.app and inspect.isclass(obj):
            return obj(j).threads, obj(j).memory_in_gb * 10 ** 9
    return None, None


def host_fit(j):
    threads_needed, memory_needed = app_limit(j)
    docker_hosts = list(dockers.values())
    random.shuffle(docker_hosts)
    for d in docker_hosts:
        info = d['docker'].info()
        cpu_needed = threads_needed * 10 ** 9 / info['NCPU'] if threads_needed else 10 ** 9
        memory_needed = memory_needed if memory_needed else info['MemTotal'] * 10 ** 9  # todo replace by max
        mem_sched = sum([d['api'].inspect_container(c)['HostConfig']['Memory'] for c in d['api'].containers()])
        cpu_sched = sum([d['api'].inspect_container(c)['HostConfig']['NanoCpus'] for c in d['api'].containers()])
        # log.debug("mem total %s %s", info['MemTotal'] , mem_sched)
        mem_avai = max(0, info['MemTotal'] - mem_sched)
        cpu_avai = 10 ** 9 - cpu_sched
        log.debug("host_fit called for job %s:%s : %03d %03d - available %03d %03d",
                  j.app, j._id, memory_needed, cpu_needed, mem_avai, cpu_avai)
        if mem_avai >= memory_needed and cpu_avai >= cpu_needed:
            return d


def main():
    while True:
        for r in client.orqal.jobs.find({'current_status': None}):
            id_ = r['_id']
            j = Job(id_)
            j.load()
            log.debug("Job to launch %s", j)
            d = host_fit(j)
            if d:
                j.status('init')
                threading.Thread(target=worker, args=(j, d)).start()
                time.sleep(1)  # in order to retrieve stats
            else:
                log.debug("No ressource available for job %s", j)
        print('Wait ...')
        time.sleep(5)


if __name__ == '__main__':
    main()
