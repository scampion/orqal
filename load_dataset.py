import hashlib, os, sys

from pymongo import MongoClient

client = MongoClient("mongodb://madlab/madlab")


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


dir = sys.argv[1]
total = 0
for root, subdirs, files in os.walk(dir):
    for f in files:
        if f.endswith('zip'):
            continue
        else:
            p = os.path.join(root, f)
            src = p.split(os.path.sep)[2]
            with open(p, "rb") as f:
                bytes = f.read()
                total += len(bytes)
                readable_hash = hashlib.md5(bytes).hexdigest()
                print(sizeof_fmt(total), {'_id': readable_hash, "path": p, "src": src})
                client.madlab.dataset.update({'_id': readable_hash}, {"path": p, "src": src}, True)
