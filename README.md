# MADLAB python library 


## Description
MADLAB is a SaaS (Software as a Service) platform provided by LHS. 

## Install 

``` 
  pip install madlab
``` 


## Setup 

```	
   python setup.py bdist
   python3 setup.py sdist
   twine upload dist/*
```

## Dev environmenmt

    MADLAB_HOST="http://localhost:5000"
	
	
## Run 

    gunicorn app:app --bind 0.0.0.0:5001 --worker-class aiohttp.GunicornWebWorker  --workers 8

	

## On docker node :

Add in file `/etc/systemd/system/docker.service.d/override.conf`

    [Service]
    ExecStart=
    ExecStart=/usr/bin/docker daemon -H fd://  -H tcp://0.0.0.0:2376 -s overlay --insecure-registry madlab:5000
    

Then flush changes by executing :
    
    systemctl daemon-reload

verify that the configuration has been loaded:
    
    systemctl show --property=ExecStart docker

restart docker:
    
    systemctl restart docker
