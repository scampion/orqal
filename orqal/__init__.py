import getpass
import json
import logging
import os
import time
import requests

ORQAL_API_URL = os.environ.get("ORQAL_API_URL", "http://localhost:5001/api")

logging.getLogger("requests").setLevel(logging.WARNING)
log = logging.getLogger('orqal')
log.setLevel(logging.DEBUG)


def services():
    try:
        return requests.get(ORQAL_API_URL + "/status").json()['_services']
    except Exception as e:
        log.error(str(e))


def wait(jobs):
    in_progress = jobs.copy()
    while in_progress:
        for j in in_progress:
            if j.load() in ['exited', 'error']:
                in_progress.remove(j)
        time.sleep(1)


def batch(jobs, name=None, slice_size=1000):
    def sliceup(size, large_list):
        for i in range(0, len(large_list), size):
            yield large_list[i:i + size]

    url = ORQAL_API_URL + "/batch"
    if name:
        url += "/" + name
        r = requests.get(url)
        if r.status_code == 200:  # batch already exist ?
            return [Job(id=v['$oid']) for v in r.json()['jobs']]

    results = []
    for slice in sliceup(slice_size, jobs):  # slice array due to request hang after ~23 000 jobs
        gen_jobs = (json.dumps(j.__dict__).encode('utf-8') for j in slice)
        results += [Job(id=c.hex()) for c in requests.post(url, data=gen_jobs, stream=True).iter_content(chunk_size=12)]
    # nb: ObjectId is a 12-byte unique identifier
    return results


class Job:

    def __init__(self, id=None, app=None, input=None, params={}, start=False):
        self._id = id
        self.app = app
        self.input = input
        self.params = params
        self.user = getpass.getuser()
        self.current_status = None
        self.container = None
        self.lswd = []
        self.stdout = []
        self.stderr = []
        self.result = None
        if start:
            self.create()

    @property
    def files(self):
        return {f: ORQAL_API_URL + "/job/%s/download/%s" % (self._id, f) for f in self.lswd}

    def status(self, s):
        self.current_status = s
        self.save()

    def load(self):
        url = ORQAL_API_URL + "/job/%s" % self._id
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        self.__dict__.update(data)
        return self.current_status

    def create(self):
        url = ORQAL_API_URL + "/job"
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
