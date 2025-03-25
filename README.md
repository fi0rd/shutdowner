# shutdowner

Run API and worker: 

$ uvicorn --port 8001 main:repairnet_app
$ uvicorn main:admin_app --port 8002 --reload
$ arq core.scheduler.WorkerSettings