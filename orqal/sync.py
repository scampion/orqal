from pymongo import ReturnDocument
from threading import Thread
import time
import logging

from mongolog import MongoHandler

from orqal.worker import mongo, dockers

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('sync')
log.addHandler(MongoHandler.to(db='orqal', collection='log'))


def sync():
    def containers():
        for d in dockers.values():
            for c in d['api'].containers():
                yield c

    def state_from_container(j):
        for c in containers():
            if j['container_id'] == c['Id']:
                log.info("Found container : %s %s", j['container_id'], c['State'])
                return c['State']
        log.warning("Container not found for job : %s", j['_id'])
        return 'exited'

    for job in mongo.orqal.jobs.find({'current_status': 'running'}):
        log.debug("Check job %s", job['_id'])
        mongo.orqal.jobs.find_one_and_update({'_id': job['_id']},
                                             {'$set': {'current_status': state_from_container(job)}})

    for c in containers():
        if c['State'] == 'exited':
            c.remove()


class SyncThread(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        r = mongo.orqal.lock.find_one_and_update(
            {'_id': 'sync'},
            {'$inc': {'seq': 1}},
            projection = {'seq': True, '_id': False},
            upsert = True,
            return_document = ReturnDocument.AFTER)
        if r['seq'] == 1 :
            try:
                log.info("Clean container and sync DB")
                sync()
            finally:
                mongo.orqal.lock.update({'_id': 'sync'}, {'seq': 0})
        else:
            log.warning("Sync thread canceled, locked")



if __name__ == '__main__':
    SyncThread().start()
    time.sleep(1)
    SyncThread().start()
