import hashlib, os, sys
import json

from pymongo import MongoClient

client = MongoClient("mongodb://madlab/madlab")


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


with open(sys.argv[1]) as jsonfile:
    data = json.load(jsonfile)
    for f in data:
        print(f)
        _id = f['_id']
        del f['_id']
        client.madlab.dataset.update_one({'_id': _id}, {'$push': f}, upsert=True)
