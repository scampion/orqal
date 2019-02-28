import logging
import time

try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError

log = logging.getLogger('madlab')
__version__ = '0.0.1'



class Job:
    def __init__(self, id, input, params, mongourl=None):
        self.container = None
        self.log = logging.getLogger("Job:%s" % id)
        self.id = id
        self.input = input
        self.params = params
        if mongourl:
            self.load()
        self.mongo_url = mongourl
        self.current_status = None
        self.logs = []

    def status(self, s):
        self.current_status = s
        self.save()

    def parse_logs(self, logs):
        for l in logs.decode('utf8').split('\n'):
            self.log.debug("job id %s - %s", self.id, l)
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
        if self.mongo_url:
            print("TODO")

    def load(self):
        print("TODO")

    def result(self, data):
        print(data) # save results #FIXME
