import collections
import concurrent
import datetime
import inspect
import json
import logging
import math
import os
import pymongo
import shutil
import sys

import aiohttp_jinja2 as aiohttp_jinja2
import docker
import jinja2
from aiohttp import web
from aiohttp_swagger import setup_swagger
from bson import ObjectId
from bson.json_util import dumps
from mongolog.handlers import MongoHandler
from pymongo import MongoClient, DESCENDING

from . import conf

mongo = MongoClient(conf.mongourl, replicaSet=conf.mongo_replicaset)

routes = web.RouteTableDef()

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('app')
log.addHandler(MongoHandler.to(db='orqal', collection='log'))


# HTML
########################################################################################################################
@routes.get('/')
@aiohttp_jinja2.template('index.html')
async def html_index(request):
    return {}


@routes.get('/doc')
@aiohttp_jinja2.template('doc.html')
async def html_doc(request):
    return {}


@routes.get('/jobs/{status}')
@routes.get('/jobs/{status}/{page}')
@aiohttp_jinja2.template('jobs.html')
async def html_jobs_status(request):
    status = mongostatus = request.match_info.get('status')
    if mongostatus == "todo":
        mongostatus = None
    page = request.match_info.get('page')
    if page is None:
        page = 1
    else:
        page = int(page)
    nbpages = math.ceil(mongo.orqal.jobs.count({'current_status': mongostatus}) / conf.nb_disp_jobs)
    jobs = list(mongo.orqal.jobs.find({'current_status': mongostatus}).skip((page - 1) * conf.nb_disp_jobs).limit(
        conf.nb_disp_jobs).sort("ctime", DESCENDING))
    headers = ['_id', 'ctime', 'current_status', 'host', 'container_id', 'image', 'input', 'wd']
    logs = [[j.get(key, '') for key in headers] for j in jobs]
    return {'status': status, 'headers': headers, 'logs': logs, 'nbpages': nbpages, 'currentpage': page}


@routes.get('/logs/{process}')
@aiohttp_jinja2.template('logs.html')
async def html_logs(request):
    process = request.match_info.get('process')
    logs = list(mongo.orqal.log.find({'module': process}).sort([("time", pymongo.DESCENDING)]))
    headers = ['levelname', 'time', 'message']
    logs = [[j.get(key, '') for key in headers] for j in logs]
    return {'process': process, 'logs': logs}


# API
########################################################################################################################
@routes.get('/api/job/{id}', allow_head=False)
async def job_get(request):
    """
    ---
    summary:  Retrieve job informations
    parameters:
        - in: path
          name: id
          schema:
            type: hexstring
          required: true
          description: bson object ID of the job to get
    produces:
    - application/json
    responses:
        "200":
            description: a job in dictionary format
    """
    id = request.match_info.get('id')
    data = mongo.orqal.jobs.find_one({'_id': ObjectId(id)})
    if len(data) == 0:
        web.Response(status=404)
    else:
        data['_id'] = id
        return web.Response(body=dumps(data), content_type='application/json')


@routes.post('/api/job')
async def job_post(request):
    """
    ---
    summary:  Create a job
    parameters:
        - in: body
          name: data
          description: The job to create.
          schema:
            type: object
            required:
              - app
              - input
            properties:
              app:
                type: string
              input:
                type: string
              params:
                type: object
    produces:
    - text/plain
    responses:
        "200":
            description: a job identifier
    """
    data = await request.json()
    if data is None:
        web.Response(status=500)
    del data['_id']
    data['ctime'] = datetime.datetime.now()
    log.debug("post job from %s for %s", request.transport.get_extra_info('peername'), data)
    _id = mongo.orqal.jobs.insert(data)
    return web.Response(text=str(_id))


@routes.get('/api/jobs/status', allow_head=False)
async def jobs_status(request):
    """
    ---
    summary:  Retrieve counters of job per status
    produces:
    - application/json
    responses:
        '200':
          description: a dictionary of status counter
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    description: The job status.
                  counter:
                    type: integer
                    description: The number of job in this job.
    """
    status_list = mongo.orqal.jobs.find().distinct('current_status')
    status = {s: mongo.orqal.jobs.find({'current_status': s}).count() for s in status_list}
    status['todo'] = status.pop(None) if None in status.keys() else 0
    return web.json_response(status, headers={'Access-Control-Allow-Origin': "*"})


@routes.get('/api/job/{id}/download/{path}', allow_head=False)
async def download_job_file(request):
    """
    ---
    summary:  Download a job file
    description: job can produce file, this route enable to download it.
    parameters:
    - in: path
      name: id
      schema:
        type: hexstring
      required: true
      description: bson object ID of the job to get
    - in: path
      name: path
      schema:
        type: string
      required: true
      description: path of the file
    produces:
    - application/octet-stream
    responses:
        "200":
          description: return the file
    """
    id = request.match_info.get('id')
    path = request.match_info.get('path')
    filepath = os.path.join(conf.jobs_dir, id, path)
    return web.FileResponse(filepath)


@routes.post('/api/batch')
@routes.post('/api/batch/{id}')
async def batch_post(request):
    """
    ---
    summary:  Speed up batch submission
    description: Reduce http transfert receive an http stream Transfer-Encoding chunked of json.
    parameters:
    - in: id
      name: id
      schema:
        type: string
      required: false
      description: a batch identifier (if already exist is overwrited)
    produces:
    - application/octet-stream
    responses:
        "200":
          description: response another http stream with object id bson encoded on 12 bytes when job is inserted
    """
    batch_id = request.match_info.get('id', None)
    jobs = []
    resp = web.StreamResponse(status=200, reason='OK', headers={'Content-Type': 'text/plain'})
    await resp.prepare(request)
    buffer = b''
    async for data, complete in request.content.iter_chunks():
        buffer = buffer + data
        if complete:
            data = json.loads(buffer.decode('utf-8'))
            del data['_id']
            data['ctime'] = datetime.datetime.now()
            _id = mongo.orqal.jobs.insert(data)
            jobs.append(_id)
            await resp.write(_id.binary)
            log.debug("batch %s %s %s", _id, data['input'], data['app'])
            buffer = b''
    if batch_id:
        mongo.orqal.batch.update({'_id': batch_id}, {'$set': {'jobs': jobs}}, upsert=True)
    return resp


@routes.get('/api/batch/{id}')
async def batch_get(request):
    """
    ---
    summary:  Retrieve job per batch identifier
    parameters:
    - in: path
      name: id
      schema:
        type: string
      required: true
      description: a batch identifier

    produces:
    - application/json
    responses:
        "200":
          description: response a jobs identifier array
    """
    batch_id = request.match_info.get('id')
    data = mongo.orqal.batch.find_one({'_id': batch_id})
    if data:
        return web.Response(body=dumps(data), content_type='application/json')
    else:
        return web.Response(body="Not found", status=404)


@routes.get('/api/stream/http://{host}/{id}')
async def stream_get(request):
    """
    ---
    summary:  Retrieve log stream from container id
    parameters:
    - in: path
      name: host
      schema:
        type: string
      required: true
      description: a host ip
    - in: path
      name: id
      schema:
        type: string
      required: true
      description: a container identifier

    produces:
    - text/plain
    responses:
        "200":
          description: stream from container logs
    """
    host = request.match_info.get('host')
    id = request.match_info.get('id')
    client = docker.DockerClient(base_url=host, version=conf.docker_api_version)

    if id not in [c.id for c in client.containers.list()]:
        return web.Response(status=404)
    container = client.containers.get(id)

    resp = web.StreamResponse(status=200,
                              reason='OK',
                              headers={'Content-Type': 'text/plain'})
    await resp.prepare(request)
    for log in container.attach(stdout=True, stderr=True, logs=True, stream=True):
        await resp.write(log)
    await resp.write_eof()
    return resp


@routes.get('/api/load', allow_head=False)
async def load(request):
    """
    ---
    summary:  Retrieve load of cluster nodes
    produces:
    - application/json
    responses:
        '200':
          description: a dictionary of status counter
          content:
            application/json:
              schema:
                type: object
                properties:
                  host:
                    type: string
                    description: The host node.
                  metrics:
                    type: object
                    description: mem, cpu, images, ...
                    properties:
                      mem:
                        type: number
                        description: memory load scheduled between 0 and 1
                      cpu:
                        type: number
                        description: cpu load scheduled between 0 and 1
                      images:
                        type: object
                        properties:
                          image_name:
                            type: integer
                            description: number of container currently running
    """

    def load_metrics():
        for h in conf.docker_hosts:
            cpu_used = 0
            mem_used = 0
            images = []
            client = docker.DockerClient(base_url=h, version=conf.docker_api_version)
            mem_total = client.info()['MemTotal']
            # docker stats need 1 second to collect stats we // that
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                images.extend([''.join(c.attrs['Config']["Image"]) for c in client.containers.list()])
                future_to_stats = {executor.submit(c.stats, stream=False): c for c in client.containers.list()}
                for future in concurrent.futures.as_completed(future_to_stats):
                    try:
                        stat = future.result()
                        cpu_delta = stat['cpu_stats']['cpu_usage']['total_usage'] - stat['precpu_stats']['cpu_usage'][
                            'total_usage']
                        sys_delta = stat['cpu_stats']['system_cpu_usage'] - stat['precpu_stats']['system_cpu_usage']
                        if cpu_delta > 0 and sys_delta > 0:
                            cpu_used += cpu_delta / sys_delta * 100.0
                        mem_used += stat['memory_stats']['usage']
                    except Exception as exc:
                        log.error(exc)
            yield {h: {'mem': mem_used / mem_total * 100.0,
                       "cpu": cpu_used,
                       'images': collections.Counter(images)}}

    return web.json_response(list(load_metrics()))


@routes.get('/api/clean/{action}', allow_head=False)
async def clean(request):
    """
    ---
    summary:  Drop all jobs in db and all containers in the cluster
    parameters:
    - in: path
      name: action
      schema:
        type: string
      required: true
      description: action all: remove all jobs + containers / scheduled: remove job execpt exited + containers
    """

    def containers_to_kill(client):
        for c in client.containers.list():
            if conf.protected_containers and c.name in conf.protected_containers:
                continue
            else:
                yield c

    def kill_and_remove(c):
        c.kill()
        c.remove()

    action = request.match_info.get('action')
    if action == 'all':
        mongo.orqal.jobs.delete_many({})
        return web.Response(text='all jobs purged', status=200)
    elif action == 'scheduled':
        mongo.orqal.jobs.delete_many({'current_status': {'$ne': 'exited'}})
        return web.Response(text='all jobs scheduled purged', status=200)
    elif action == 'old':
        resp = web.StreamResponse(status=200, reason='OK', headers={'Content-Type': 'text/plain'})
        await resp.prepare(request)
        for d in os.listdir(conf.jobs_dir):
            if not mongo.orqal.jobs.find_one({'_id': d}):
                log.debug("delete dir %s", d)
                shutil.rmtree(os.path.join(conf.jobs_dir, d))
                await resp.write(bytes("%s\n" % d, "utf8"))
        return resp
    elif action == 'containers':
        for h in conf.docker_hosts:
            client = docker.DockerClient(base_url=h, version=conf.docker_api_version)
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                future_to_stats = {executor.submit(kill_and_remove, c): c for c in containers_to_kill(client)}
                for future in concurrent.futures.as_completed(future_to_stats):
                    try:
                        future.result()
                    except Exception as exc:
                        log.error(exc)
            return web.Response(text='containers removed', status=200)
    else:
        return web.Response(text='action in path needed', status=500)


@routes.get('/api/status', allow_head=False)
async def status(request):
    """
    ---
    summary:  Global status description
    produces:
    - application/json
    """
    import wrapper
    def containers():
        for d in dockers.values():
            yield {
                d['docker'].info()['Name']: [(c.id, c.image.tags[0], c.status) for c in d['docker'].containers.list()]}

    dockers = {h: {'docker': docker.DockerClient(base_url=h, version=conf.docker_api_version),
                   'api': docker.APIClient(base_url=h, version=conf.docker_api_version)
                   } for h in conf.docker_hosts}

    status_list = mongo.db.jobs.find().distinct('current_status')
    status = {s: mongo.db.jobs.find({'current_status': s}).count() for s in status_list}
    s = {"_id": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         "_doc": __doc__,
         "status": status,
         "_services": [name for name, obj in inspect.getmembers(sys.modules["wrapper"]) if inspect.isclass(obj)],
         "hosts": conf.docker_hosts,
         "nodes": {ip: {"info": d['docker'].info(),
                        "containers": [d['api'].inspect_container(c) for c in d['api'].containers()]}
                   for ip, d in dockers.items()},
         "containers": [c for c in containers()]
         }
    return web.json_response(s)


app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./templates'))
for d in ['assets', 'images', 'vendors']:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app.router.add_static('/' + d, path=os.path.join(current_dir, 'static', d), name=d)
app.add_routes(routes)

setup_swagger(app,
              description="Scalable cluster management and job scheduling system for large and small Docker clusters",
              title="orqal",
              api_version="1.0",
              contact=conf.contact)

def main():
    web.run_app(app, port=5001)


if __name__ == '__main__':
    main()
