import json
import logging
import os
import time

import requests

log = logging.getLogger('madlab')
__version__ = '0.0.1'

MADLAB_HOST = os.environ.get("MADLAB_HOST", "http://localhost:5000")

logging.basicConfig(level=logging.DEBUG)


def wait(jobs):
    while not all([j.current_status == 'finish' for j in jobs]):
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
        # self.__dict__.pop('_id')
        r = requests.post(url, data=json.dumps(self.__dict__))
        r.raise_for_status()
        self._id = r.content.decode('utf8')
        assert self._id, "Cannot create job"
        self.load()

    def __str__(self):
        return "Job <%s | %s | %s | %s>" % (self._id, self.app, self.input, self.current_status)


if __name__ == '__main__':
    j = Job(app="Test", input=None, params={"app": {'echo': 'test', 'time': 10, 'exit_code': 2}})
    print(j.current_status)
    wait([j])
