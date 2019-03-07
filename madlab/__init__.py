import json
import logging
import os
import time

import requests


__version__ = '0.0.2'
MADLAB_HOST = os.environ.get("MADLAB_HOST", "http://madlab.irisa.fr:5001")

logging.getLogger("requests").setLevel(logging.WARNING)
log = logging.getLogger('madlab')
log.setLevel(logging.DEBUG)

try:
    services = requests.get(MADLAB_HOST).json()['_services']
except Exception as e:
    log.error(str(e))


def wait(jobs):
    while not all([j.current_status in ['exited', 'error'] for j in jobs]):
        for j in jobs:
            j.load()
        time.sleep(5)


class Job:

    def __init__(self, id=None, app=None, input=None, params={}):
        self._id = id
        self.app = app
        self.input = input
        self.params = params
        self.current_status = None
        self.container = None
        self.logs = []
        self.result = None
        if self._id:
            self.load()
        else:
            log.info("Create job for app %s input %s", app, input)
            self.create()

    def status(self, s):
        self.current_status = s
        self.save()

    def load(self):
        url = MADLAB_HOST + "/job/%s" % self._id
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        self.__dict__.update(data)

    def create(self):
        url = MADLAB_HOST + "/job"
        r = requests.post(url, data=json.dumps(self.__dict__))
        r.raise_for_status()
        self._id = r.content.decode('utf8')
        assert self._id, "Cannot create job"
        self.load()

    def __str__(self):
        return "Job <%s | %s | %s | %s>" % (self._id, self.app, self.input, self.current_status)

    def __repr__(self):
        r = "Job %s | app: %s | input: %s | status: %s" % (self._id, self.app, self.input, self.current_status)
        if len(self.logs):
            r += "\nlogs :\n"
            r += "-"*80 + '\n'
            r += "\n".join(self.logs)
        return r


if __name__ == '__main__':
    j = Job(app="Test", input=None, params={"app": {'echo': 'test', 'time': 10, 'exit_code': 2}})
    print(j.current_status)
    wait([j])
