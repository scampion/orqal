mongourl = "mongodb://localhost/orqal"

docker_hosts = ['192.168.100.%d:2376' % i for i in range(51, 65)]
docker_api_version = '1.37'
auth_config = {'username': 'test',
               'password': '65sX2-9sSXSp-hs-XeZ8'}
jobs_dir = "/scratch/jobs"
graphana_url = "http://localhost:3000/dashboard/db/docker-and-system-monitoring"
protected_containers = ['cadvisor']