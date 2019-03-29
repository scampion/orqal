import datetime
import inspect
import sys

import docker
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask import Flask, request, abort
from flask_pymongo import PyMongo

import conf, wrapper

app = Flask(__name__)
app.config["MONGO_URI"] = conf.mongourl
mongo = PyMongo(app)

status_list = mongo.db.jobs.find().distinct('current_status')


@app.route('/')
def index():
    def containers():
        for d in dockers.values():
            yield {
                d['docker'].info()['Name']: [(c.id, c.image.tags[0], c.status) for c in d['docker'].containers.list()]}

    dockers = {h: {'docker': docker.DockerClient(base_url=h, version=conf.docker_api_version),
                   'api': docker.APIClient(base_url=h, version=conf.docker_api_version),
                   'model': m}
               for h, m in conf.docker_hosts.items()}

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
    return dumps(s), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/job', methods=['POST'])
def create_job():
    data = request.get_json(force=True)
    if data is None:
        abort(500)
    del data['_id']
    data['ctime'] = datetime.datetime.now()
    _id = mongo.db.jobs.insert(data)
    return str(_id)


@app.route('/job/<id>')
def get_job(id):
    data = mongo.db.jobs.find_one_or_404({'_id': ObjectId(id)})
    data['_id'] = id
    return dumps(data)


@app.route('/jobs/status')
def get_jobs_status():
    data = request.get_json()
    if data is None or request.method == 'GET':
        return dumps({s: mongo.db.jobs.find({'current_status': s}).count() for s in status_list})
    else:
        jobs = mongo.db.jobs.aggregate(
            [{'$group': {'_id': {'status': '$status'}, 'ids': {'$addToSet': {
                '$toString': "$_id"
            }}}}])
        return dumps(jobs)

@app.route('/dataset.json')
def dataset():
    return dumps(mongo.db.dataset.find())


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
