import getpass
import json
import logging
import os
import time
import requests

__version__ = '0.0.4'
MADLAB_API_URL = os.environ.get("MADLAB_API_URL", "http://madlab.irisa.fr:5001/api")

logging.getLogger("requests").setLevel(logging.WARNING)
log = logging.getLogger('madlab')
log.setLevel(logging.DEBUG)

services = []
try:
    services = requests.get(MADLAB_API_URL + "/status").json()['_services']
except Exception as e:
    log.error(str(e))


def wait(jobs):
    in_progress = jobs
    while in_progress:
        for j in jobs:
            if j.load() in ['exited', 'error']:
                in_progress.remove(j)
        time.sleep(1)


def batch(jobs, name=None):
    url = MADLAB_API_URL + "/batch"
    if name:
        url += "/" + name
    gen_jobs = (json.dumps(j.__dict__).encode('utf-8') for j in jobs)
    return [Job(id=c.hex()) for c in requests.post(url, data=gen_jobs, stream=True).iter_content(chunk_size=12)]
    # nb: ObjectId is a 12-byte unique identifier


class Job:

    def __init__(self, id=None, app=None, input=None, params={}, start=False):
        self._id = id
        self.app = app
        self.input = input
        self.params = params
        self.user = getpass.getuser()
        self.current_status = None
        self.container = None
        self.stdout = []
        self.stderr = []
        self.result = None
        if self._id:
            self.load()
        elif start:
            self.create()

    def status(self, s):
        self.current_status = s
        self.save()

    def load(self):
        url = MADLAB_API_URL + "/job/%s" % self._id
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        self.__dict__.update(data)
        return self.current_status

    def create(self):
        url = MADLAB_API_URL + "/job"
        r = requests.post(url, data=json.dumps(self.__dict__))
        r.raise_for_status()
        self._id = r.content.decode('utf8')
        assert self._id, "Cannot create job"
        self.load()

    def __str__(self):
        return "Job <%s | %s | %s | %s>" % (self._id, self.app, self.input, self.current_status)

    def __repr__(self):
        r = "Job %s | app: %s | input: %s | status: %s" % (self._id, self.app, self.input, self.current_status)
        if len(self.stdout):
            r += "\nstdout :\n"
            r += "-" * 80 + '\n'
            r += "\n".join(self.stdout)
        return r


if __name__ == '__main__':
    j = Job(app="Test", input=None, params={"app": {'echo': 'test', 'time': 10, 'exit_code': 2}})
    wait([j])
