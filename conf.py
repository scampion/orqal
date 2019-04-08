mongourl = "mongodb://localhost/madlab"
Cisco_UCS_B200_M4 = {'cpu': 2, 'cores': 28, 'threads': 56, 'memory_in_gb': 128}
docker_hosts = {'192.168.100.51:2376': Cisco_UCS_B200_M4,
                '192.168.100.52:2376': Cisco_UCS_B200_M4}
docker_api_version = '1.37'
auth_config = {'username': 'scampion',
               'password': '65sX2-9sSXSp-hs-XeZ8'}
jobs_dir = "/scratch/jobs"
graphana_url = "http://madlab.irisa.fr:3000/dashboard/db/docker-and-system-monitoring"
