"""
Conf using built-in data structures and dynamic loading

"""
import os
import sys

fp = os.path.expanduser(os.path.join('~', '.orqal', 'conf.py'))
if os.path.exists(fp):
    sys.path.append(os.path.expanduser(os.path.join('~', '.orqal')))
    from conf import *
else:
    mongourl = os.environ.get("ORQAL_MONGO_URL", "mongodb://localhost/orqal")
    docker_hosts = ['192.168.100.%d:2376' % i for i in range(51, 65)]
    mongo_replicaset = "madlabReplSet"
    docker_api_version = '1.37'
    registry_auth_config = {'username': 'test',
                            'password': '65sX2-9sSXSp-hs-XeZ8'}
    jobs_dir = "/scratch/jobs"
    graphana_url = "http://localhost:3000/dashboard/db/docker-and-system-monitoring"
    protected_containers = ['cadvisor']
    nb_disp_jobs = 20
    contact = "orqal@inria.fr"