import json
import logging
import conf
import os


class AbstractWrapper:
    docker_url = None
    volumes = None
    volumes = {'/scratch': {'bind': '/scratch', 'mode': 'rw'},
               '/database': {'bind': '/database', 'mode': 'ro'}}

    threads = None  # mean take all cores available on host by default
    memory_in_gb = None  # idem for memory
    create_dir = False

    def __init__(self, job):
        self.log = logging.getLogger(str(self.__class__))
        self.job = job
        if self.create_dir and not os.path.exists(self.job.wd):
            self.setup_dir()

    def setup_dir(self):
        os.mkdir(self.job.wd, 0o777)
        os.chmod(self.job.wd, 0o777)  # strange behaviour due to nfs ? we must set permission after
        with open(os.path.join(self.job.wd, 'params.json'), 'w') as f:
            json.dump(self.job.params, f)

    def run(self, docker, tag='latest'):
        client = docker['docker']
        self.log.debug("Pull image %s", self.docker_url)
        client.images.pull(self.docker_url, tag, auth_config=conf.auth_config)
        mem_limit = int(self.memory_in_gb * 10 ** 9 if self.memory_in_gb else client.info()['MemTotal'])
        cpu_count = self.threads if self.threads else client.info()['NCPU']
        cmd = self.get_cmd(self.job.params.get('app', None))
        self.job.host = client.api.base_url
        self.job.image = self.docker_url + ':' + tag
        self.job.cmd = cmd
        name = "%s_%s" % (self.docker_url.split('/')[-1], self.job._id)
        self.job.run(docker['api'],
                     client.containers.run(self.docker_url + ':' + tag,
                                           cmd, mem_limit=mem_limit, cpu_count=cpu_count,
                                           volumes=self.volumes, working_dir=self.job.wd,
                                           detach=True, auto_remove=False, name=name))

        self.set_result(self.job)


########################################################################################################################

class TestProd(AbstractWrapper):
    docker_url = "madlab:5000/test_module"

    def get_cmd(self, params):
        return "python3 simple_job.py %s %s %s" % (params['echo'], params['time'], params['exit_code'])

    def set_result(self, job):
        job.set_result("My results")


class AngrExtraction(AbstractWrapper):
    docker_url = "madlab:5000/scdg/madlab-v2"
    threads = 1
    memory_in_gb = 10
    create_dir = True

    def get_cmd(self, params):
        return "python /code/src/interfaces/cli.py %s params.json -o calls.json" % self.job.input

    def set_result(self, job):
        return os.path.join(self.job.wd, "calls.json")


class Rabin2(AbstractWrapper):
    docker_url = "madlab:5000/radare2"
    volumes = {'/database': {'bind': '/database', 'mode': 'ro'}}
    threads = 1
    memory_in_gb = 1

    def get_cmd(self, params):
        return "rabin2 -I %s" % self.job.input

    def set_result(self, job):
        r = {l.split()[0].replace('.', '_'): l.split()[1] for l in job.stdout if len(l.split()) == 2}
        job.set_result(r)


class Test(AbstractWrapper):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/test_module"

    def get_cmd(self, params):
        return "python3 simple_job.py %s %s %s" % (params['echo'], params['time'], params['exit_code'])

    def set_result(self, job):
        job.set_result("My results")


class SCDG_Extraction(AbstractWrapper):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/scdg/trace_gridfs"
    volumes = {'/scratch': {'bind': '/scratch', 'mode': 'rw'},
               '/database': {'bind': '/database', 'mode': 'ro'}}

    def get_cmd(self, params):
        return "python trace_calls.py /code/tests/binaries/pe/32/helloword.exe"

    def set_result(self, job):
        job.set_result("My results")


class VirusTotal(AbstractWrapper):
    docker_url = "registry.gitlab.inria.fr/scampion/madlab/virustotal"

    def get_cmd(self, params):
        api_key = "665a6fda794f671b77720b314944f2409429e9d9b6f62b0bdaa003fa94126ec1"
        cmd = "--api %s lookup %s" % (api_key, self.job.input)
        self.job.cmd = cmd
        return cmd

    def set_result(self, job):
        job.set_result(json.dumps(job.logs))


class SCDG(AbstractWrapper):
    #docker_url = "registry.gitlab.inria.fr/scampion/madlab/scdg/trace_gridfs"
    docker_url = "madlab:5000/scdg_graphs"
    volumes = {'/scratch': {'bind': '/scratch', 'mode': 'rw'}}
    threads = 1
    memory_in_gb = 5
    create_dir = True

    def get_cmd(self, params):
        return "python interfaces/cli.py %s params.json -o scdg.json" % self.job.input

    def set_result(self, job):
        job.set_result(os.path.join(self.job.wd, "scdg.json"))



