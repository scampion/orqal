from worker import AbstractWorker


class Rabin2(AbstractWorker):
    docker_url = "radare/radare2"
    volumes = {'/database': {'bind': '/database', 'mode': 'ro'}}
    threads = 1
    memory_in_gb = 1

    def get_cmd(self, params):
        return "rabin2 -I %s" % self.job.input

    def set_result(self, job):
        r = {l.split()[0].replace('.', '_'): l.split()[1] for l in job.stdout if len(l.split()) == 2}
        job.set_result(r)

