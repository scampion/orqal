import json
from worker import AbstractWorker


class TestProd(AbstractWorker):
    docker_url = "madlab:5000/test_module"

    def get_cmd(self, params):
        return "python3 simple_job.py %s %s %s" % (params['echo'], params['time'], params['exit_code'])

    def set_result(self, job):
        job.set_result("My results")


class SCDG(AbstractWorker):
    docker_url = "madlab:5000/scdg/madlab-v2"
    threads = 1
    memory_in_gb = 10
    create_dir = True

    def get_cmd(self, params):
        return "python /code/src/interfaces/cli.py %s params.json -o calls.json" % self.job.input

    def set_result(self, job):
        pass


class Rabin2(AbstractWorker):
    docker_url = "madlab:5000/radare2"
    volumes = {'/database': {'bind': '/database', 'mode': 'ro'}}
    threads = 1
    memory_in_gb = 1

    def get_cmd(self, params):
        return "rabin2 -I %s" % self.job.input

    def set_result(self, job):
        r = {l.split()[0].replace('.', '_'): l.split()[1] for l in job.stdout if len(l.split()) == 2}
        job.set_result(r)


class Test(AbstractWorker):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def get_cmd(self, params):
        return "python3 simple_job.py %s %s %s" % (params['echo'], params['time'], params['exit_code'])

    def set_result(self, job):
        job.set_result("My results")


class SCDG_Extraction(AbstractWorker):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/scdg/trace_gridfs"
    volumes = {'/scratch': {'bind': '/scratch', 'mode': 'rw'},
               '/database': {'bind': '/database', 'mode': 'ro'}}

    def get_cmd(self, params):
        return "python trace_calls.py /code/tests/binaries/pe/32/helloword.exe"

    def set_result(self, job):
        job.set_result("My results")


class VirusTotal(AbstractWorker):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/virustotal"

    def get_cmd(self, params):
        api_key = "665a6fda794f671b77720b314944f2409429e9d9b6f62b0bdaa003fa94126ec1"
        cmd = "--api %s lookup %s" % (api_key, self.job.input)
        self.job.cmd = cmd
        return cmd

    def set_result(self, job):
        job.set_result(json.dumps(job.logs))
