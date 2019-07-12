import os
from pymongo import MongoClient

mongourl = os.getenv("ORQAL_MONGO_URI", 'mongodb://localhost/')
print(mongourl)
mongo = MongoClient(mongourl)

mconf = {'mongourl': 'mongodb://mongo/',
           'mongo_replicaset': None,
           'docker_hosts': ['nodeA', 'nodeB'],
           'docker_api_version': '1.40',
           'registry_auth_config': {'username': 'test',
                                    'password': '65sX2-9sSXSp-hs-XeZ8'},
           'jobs_dir': "/scratch/jobs",
           'nb_disp_jobs': 30,
           'contact': "orqal@example.com",
           'services': "~/services.py", 
           'active': True
           }

dbconf = mongo.orqal.conf.find_one({'active': True})
if dbconf:
    mconf = {**mconf, **dbconf}
    mongo.orqal.conf.replace_one({'_id': mconf['_id']}, mconf)
else:
    mongo.orqal.conf.insert_one(mconf)

locals().update(mconf)
