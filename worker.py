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

import docker
import json

import conf
import madlab
import wrapper

from pymongo import MongoClient

client = MongoClient(conf.mongourl)

dockers = [docker.DockerClient(base_url=h, version=conf.docker_api_version) for h in conf.docker_hosts]
logging.getLogger("requests").setLevel(logging.WARNING)
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


def worker(j):
    log.info("Thread start : %s", j)
    for name, obj in inspect.getmembers(sys.modules["wrapper"]):
        if name != 'Job' and name == j.app and inspect.isclass(obj):
            log.info("Run %s %s", name, obj)
            try:
                obj(j).run(dockers[0])
            except Exception as e:
                j.logs.append(str(e))
                j.status("error")
    log.info("Thread stop : %s", j)


def containers():
    for d in dockers:
        yield {d.info()['Name']: [(c.id, c.image, c.status) for c in d.containers.list()]}


def status(tds):
    s = {"_id":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "_doc": __doc__,
           "_last_update":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "_services": [name for name, obj in inspect.getmembers(sys.modules["wrapper"]) if inspect.isclass(obj)],
           "hosts": conf.docker_hosts,
           "nodes": [d.info() for d in dockers],
           "containers": [c for c in containers()],
           "threads": {str(j): t.getName() for j, t in tds.items()},
           }
    client.madlab.status.insert(s, check_keys=False)


def main():
    threads = {}
    status(threads)
    while True:
        for r in client.madlab.jobs.find({'current_status': None}):
            id_ = r['_id']
            j = Job(id_)
            j.status('init')
            t = threading.Thread(target=worker, args=(j,))
            threads[id_] = t
            t.start()
        if len(threads) > conf.max_threads:
            time.sleep(5)
        time.sleep(5)
        status(threads)


if __name__ == '__main__':
    main()
