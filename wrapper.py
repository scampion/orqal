import json
import logging

import conf


class AbstractWorker:
    docker_url = None
    volumes = None

    def __init__(self, job):
        self.log = logging.getLogger(str(self.__class__))
        self.job = job

    def run(self, client, tag='latest'):
        self.log.debug("Pull image %s", self.docker_url)
        client.images.pull(self.docker_url, tag, auth_config=conf.auth_config)

        cmd = self.get_cmd(self.job.params.get('app', None))
        self.job.run(client.containers.run(self.docker_url + ':' + tag,
                                           cmd,
                                           volumes=self.volumes,
                                           detach=True, auto_remove=conf.auto_remove))
        self.set_result(self.job)


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
        api_key  = "665a6fda794f671b77720b314944f2409429e9d9b6f62b0bdaa003fa94126ec1"
        cmd = "--api %s lookup %s" % (api_key, self.job.input)
        self.job.cmd = cmd
        return cmd

    def set_result(self, job):
        job.set_result(json.dumps(job.logs))