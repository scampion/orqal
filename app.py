import json

from flask import Flask, request, abort, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from bson.json_util import dumps

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/madlab"
mongo = PyMongo(app)


@app.route('/')
def index():
    with open('status.json') as s:
        return s.read()


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
    app.run(debug=True)
