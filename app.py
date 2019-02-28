from flask import Flask, request, abort, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from bson.json_util import dumps

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/madlab"
mongo = PyMongo(app)


@app.route('/')
@app.route('/index')
def index():
    return "MADLAB - WIP"


@app.route('/job', methods=['POST'])
def create_job():
    data = request.get_json()
    if data is None:
        abort(500)
    app = data.get('app', None)
    input_file = data.get('input', None)
    params = data.get('params', None)
    _id = mongo.db.jobs.insert(
        {'app': app, 'input': input_file, 'params': params})
    return str(_id)


@app.route('/job/<id>')
def get_job(id):
    return dumps(mongo.db.jobs.find_one_or_404({'_id': ObjectId(id)}))


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
    app.run()
