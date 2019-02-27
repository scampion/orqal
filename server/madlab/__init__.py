import logging
import os
import time

try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError
import requests

log = logging.getLogger('madlab')
__version__ = '0.0.1'


class Job:
    def __init__(self, id, mongourl=None):
        self.id = id
        if mongourl:
            self.load()
        self.mongo_url = mongourl
        self.current_status = None
        self.logs = []

    def status(self, s):
        self.current_status = s
        self.save()

    def logs(self, l):
        self.logs.append(l)
        self.save()

    def save(self):
        if self.mongo_url:
            print("TODO")

   def load(self):
        print("TODO")
