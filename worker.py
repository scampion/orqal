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


def worker(j):
    log.info("Thread start : %s", j)
    for name, obj in inspect.getmembers(sys.modules["wrapper"]):
        if name != 'Job' and name == j.app and inspect.isclass(obj):
            log.info("Run %s %s", name, obj)
            obj(j).run(dockers[0])
    log.info("Thread stop : %s", j)


def status(tds):
    with open('status.json', 'w') as s:
        json.dump({"threads": tds}, s)
        # json.dump({"threads": {id: t.name for id, t in tds.items()}}, s)


if __name__ == '__main__':
    threads = {}
    while True:
        status(threads)
        for r in client.madlab.jobs.find({'current_status': None}):
            id_ = r['_id']
            j = Job(id_)
            j.status('init')
            t = threading.Thread(target=worker, args=(j,))
            threads[id_] = t
            t.start()
        if len(threads) > conf.max_threads:
            time.sleep(5)
