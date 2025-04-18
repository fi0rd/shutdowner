# shutdowner

Сервис получает сетевые алерты о CRC ошибках (InErrors) из Clickhouse, заводит алерты в Системе, проводит проверки и выключает соответствующий интерфейс(ы).
Состоит из backend'а, написанного на FastAPI и воркера, который переодически получает данные об алертах с бекенда и взаимодействует с сетью.  

Run API and worker: 

$ uvicorn --port 8001 main:repairnet_app
$ uvicorn main:admin_app --port 8002 --reload
$ arq core.scheduler.WorkerSettings
