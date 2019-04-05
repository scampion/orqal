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
@routes.post('/batch')
async def batch(request):
    """
    ---
    description: Create to speed up batch submission and reduce http transfert.
    Receive an http stream "Transfer-Encoding: chunked" of json.
    tags:
    - Batch scheduling
    produces:
    - application/octet-stream
    responses:
        "200":
            description: response another http stream with object id bson encoded on 12 bytes when job is inserted
        "405":
            description: invalid HTTP Method
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


@routes.get('/load')
async def jobs_status(request):
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


@routes.get('/clean')
async def clean(request):
    mongo.madlab.jobs.delete_many({})
    return web.HTTPFound(location="/")


@routes.get('/status')
async def status(request):
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


@routes.post('/job')
async def create_job(request):
    data = await request.json()
    if data is None:
        web.Response(status=500)
    del data['_id']
    data['ctime'] = datetime.datetime.now()
    log.debug("post job from %s for %s", request.transport.get_extra_info('peername'), data)
    _id = mongo.madlab.jobs.insert(data)
    return web.Response(text=str(_id))


@routes.get('/jobs/status')
async def get_status(request):
    status_list = mongo.madlab.jobs.find().distinct('current_status')
    status = {s: mongo.madlab.jobs.find({'current_status': s}).count() for s in status_list}
    status['todo'] = status.pop(None) if None in status.keys() else 0
    return web.json_response(status, headers={'Access-Control-Allow-Origin': "*"})


@routes.get('/job/{id}')
async def get_job(request):
    id = request.match_info.get('id')
    data = mongo.madlab.jobs.find_one({'_id': ObjectId(id)})
    if len(data) == 0:
        web.Response(status=404)
    else:
        data['_id'] = id
        return web.Response(body=dumps(data), content_type='application/json')


@routes.get('/job/{id}/download/{path}')
async def download_job_file(request):
    id = request.match_info.get('id')
    path = request.match_info.get('path')
    filepath = os.path.join(conf.jobs_dir, id, path)
    return web.FileResponse(filepath)


@routes.get('/dataset.json')
async def dataset(request):
    return web.Response(body=dumps(mongo.madlab.dataset.find()), content_type='application/json')


app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./templates'))
app.router.add_static('/assets/', path='static/assets', name='assets')
app.router.add_static('/images/', path='static/images', name='images')
app.router.add_static('/vendors/', path='static/vendors', name='vendors')
app.add_routes(routes)
setup_swagger(app)

if __name__ == '__main__':
    web.run_app(app, port=5000)
