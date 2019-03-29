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


@app.route('/')
def index():
    def containers():
        for d in dockers.values():
            yield {d['docker'].info()['Name']: [(c.id, c.image.tags[0], c.status) for c in d['docker'].containers.list()]}

    dockers = {h: {'docker': docker.DockerClient(base_url=h, version=conf.docker_api_version),
                   'api': docker.APIClient(base_url=h, version=conf.docker_api_version),
                   'model': m}
               for h, m in conf.docker_hosts.items()}

    d = (datetime.datetime.now() - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")

    s = {"_id": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         "_doc": __doc__,
         "_last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         "_services": [name for name, obj in inspect.getmembers(sys.modules["wrapper"]) if inspect.isclass(obj)],
         "hosts": conf.docker_hosts,
         "nodes": [d['docker'].info() for d in dockers.values()],
         "containers": [c for c in containers()]
         }

    return dumps(s), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/job', methods=['POST'])
def create_job():
    data = request.get_json(force=True)
    if data is None:
        abort(500)
    del data['_id']
    _id = mongo.db.jobs.insert(data)
    return str(_id)


@app.route('/job/<id>')
def get_job(id):
    data = mongo.db.jobs.find_one_or_404({'_id': ObjectId(id)})
    data['_id'] = id
    return dumps(data)


@app.route('/jobs/status', methods=['POST'])
def get_jobs_status():
    data = request.get_json()
    if data is None:
        abort(500)
    jobs = mongo.db.jobs.aggregate(
        [{'$group': {'_id': {'status': '$status'}, 'ids': {'$addToSet': {
            '$toString': "$_id"
        }}}}])
    return dumps(jobs)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
