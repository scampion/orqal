import collections
import datetime
import inspect
import json
import os
import sys

import aiohttp_jinja2 as aiohttp_jinja2
from aiohttp_swagger import setup_swagger
import docker
import jinja2
import logging
from aiohttp import web
from bson import ObjectId
from bson.json_util import dumps
from pymongo import MongoClient

import conf

mongo = MongoClient(conf.mongourl)

routes = web.RouteTableDef()

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('madlab')


# HTML
########################################################################################################################
@routes.get('/')
@aiohttp_jinja2.template('index.html')
async def index(request):
    return {}


@routes.get('/doc')
@aiohttp_jinja2.template('doc.html')
async def doc(request):
    return {}


@routes.get('/jobs_{status}')
@aiohttp_jinja2.template('jobs.html')
async def jobs_status(request):
    status = request.match_info.get('status')
    jobs = list(mongo.madlab.jobs.find({'current_status': status}))
    headers = sorted(jobs[0].keys())
    logs = [[j[key] for key in headers] for j in jobs]
    return {'headers': headers, 'logs': logs}


# API
########################################################################################################################
@routes.get('/api/job/{id}', allow_head=False)
async def get_job(request):
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
    data = mongo.madlab.jobs.find_one({'_id': ObjectId(id)})
    if len(data) == 0:
        web.Response(status=404)
    else:
        data['_id'] = id
        return web.Response(body=dumps(data), content_type='application/json')


@routes.post('/api/job')
async def create_job(request):
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
    _id = mongo.madlab.jobs.insert(data)
    return web.Response(text=str(_id))


@routes.get('/api/jobs/status', allow_head=False)
async def get_status(request):
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
    status_list = mongo.madlab.jobs.find().distinct('current_status')
    status = {s: mongo.madlab.jobs.find({'current_status': s}).count() for s in status_list}
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
async def batch(request):
    """
    ---
    summary:  Speed up batch submission
    description: Reduce http transfert receive an http stream Transfer-Encoding chunked of json.
    produces:
    - application/octet-stream
    responses:
        "200":
          description: response another http stream with object id bson encoded on 12 bytes when job is inserted
    """
    resp = web.StreamResponse(status=200, reason='OK', headers={'Content-Type': 'text/plain'})
    await resp.prepare(request)
    buffer = b''
    async for data, complete in request.content.iter_chunks():
        buffer = buffer + data
        if complete:
            data = json.loads(buffer.decode('utf-8'))
            del data['_id']
            data['ctime'] = datetime.datetime.now()
            _id = mongo.madlab.jobs.insert(data)
            log.debug("batch %s %s %s", _id, data['input'], data['app'])
            await resp.write(_id.binary)
            buffer = b''
    return resp


@routes.get('/api/load', allow_head=False)
async def jobs_status(request):
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
                        description: memory load between 0 and 1
                      cpu:
                        type: number
                        description: cpu load between 0 and 1
                      images:
                        type: object
                        properties:
                          image_name:
                            type: integer
                            description: number of container currently running
    """
    def inspects(h):  # if container is removed during the request pass exception
        api = docker.APIClient(base_url=h, version=conf.docker_api_version)
        for c in api.containers():
            try:
                yield dict(api.inspect_container(c))
            except Exception:
                pass

    def load_metrics():
        for h, m in conf.docker_hosts.items():
            s = list(inspects(h))
            mem_used = sum(v['HostConfig']['Memory'] for v in s)
            cpu_used = sum(v['HostConfig']['NanoCpus'] for v in s)
            images = collections.Counter([v['Config']['Image'] for v in s])
            yield {h: {'mem': (mem_used / 10 ** 9 * 100.0 / m['memory_in_gb']),
                       "cpu": cpu_used / 10 ** 9 * 100.0,
                       'images': images}}

    return web.json_response(list(load_metrics()))


@routes.get('/api/clean', allow_head=False)
async def clean(request):
    """
    ---
    summary:  Drop all jobs
    """
    mongo.madlab.jobs.delete_many({})
    return web.Response(status=200)


@routes.get('/api/status', allow_head=False)
async def status(request):
    """
    ---
    summary:  Global status description
    produces:
    - application/json
    """
    def containers():
        for d in dockers.values():
            yield {
                d['docker'].info()['Name']: [(c.id, c.image.tags[0], c.status) for c in d['docker'].containers.list()]}

    dockers = {h: {'docker': docker.DockerClient(base_url=h, version=conf.docker_api_version),
                   'api': docker.APIClient(base_url=h, version=conf.docker_api_version),
                   'model': m}
               for h, m in conf.docker_hosts.items()}

    status_list = mongo.db.jobs.find().distinct('current_status')
    status = {s: mongo.db.jobs.find({'current_status': s}).count() for s in status_list}
    import wrapper
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


@routes.get('/api/dataset.json', allow_head=False)
async def dataset(request):
    """
    ---
    summary:  Retrieve dataset in order to backup it
    produces:
    - application/json
    """
    return web.Response(body=dumps(mongo.madlab.dataset.find()), content_type='application/json')


app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./templates'))
for d in ['assets', 'images', 'vendors']:
    app.router.add_static('/' + d, path=os.path.join('static', d), name=d)
app.add_routes(routes)

setup_swagger(app,
              description="Scalable cluster management and job scheduling system for large and small Docker clusters",
              title="MadLab",
              api_version="1.0",
              contact="madlab@inria.fr")

if __name__ == '__main__':
    web.run_app(app, port=5000)
