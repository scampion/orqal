from flask import Flask, request, abort

app = Flask(__name__)


@app.route('/')
@app.route('/index')
def index():
    return "MADLAB - WIP"

@app.route('/job', method='POST')
def create_job():
        data = request.get_json()
        if data is None:
            abort(500)
        app = data.get('app', None)
        inputFile = data.get('input', None)
        params = data.get('params', None)
    return "Hello, World!"
    #return {id, status, metadata, app, input, params, result, logs{stdout, stderr}}

@app.route('/job/<id>')
def get_job(id):
    return "Hello, World!"
    #return {id, status, metadata, app, input, params, result, logs{stdout, stderr}}

@app.route('/jobs/status', method='POST')
def get_jobs_status():
    try:
        data = request.get_json()
    except Exception as e:
        abort(500)
    return "Hello, World!"
    #return {finish:[], error:[],submitted}

if __name__ == '__main__':
    app.run()
