import os
from pymongo import MongoClient

mongourl = os.getenv("ORQAL_MONGO_URI", 'mongodb://localhost/')
mongo = MongoClient(mongourl)

default = {'mongourl': 'mongodb://localhost/',
           'mongo_replicaset': "madlabReplSet",
           'docker_hosts': ['192.168.100.%d:2376' % i for i in range(51, 65)],
           'docker_api_version': '1.37',
           'registry_auth_config': {'username': 'test',
                                    'password': '65sX2-9sSXSp-hs-XeZ8'},
           'jobs_dir': "/scratch/jobs",
           'nb_disp_jobs': 30,
           'contact': "orqal@example.com",
           }

dbconf = mongo.orqal.conf.find_one({'active': True})
mconf = {**default, **dbconf}
locals().update(mconf)
mongo.orqal.conf.replace_one({'_id': mconf['_id']}, mconf)
