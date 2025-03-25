import warnings

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from starlette.applications import Starlette
from api import router
from db.session import engine
from starlette_admin.contrib.sqla import Admin, ModelView
from contextlib import asynccontextmanager
from db.models import Incidents, CMDBNetworkHost, Events
from db.init_db import init_db
from dependencies import cmdb_client

warnings.simplefilter('always', ResourceWarning)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await cmdb_client.fill_cmdb()
    yield
    # release resources here
    await engine.dispose()


repairnet_app = FastAPI(lifespan=lifespan,
                        default_response_class=ORJSONResponse,
                        )
repairnet_app.include_router(router)

# run web-admin as:
# uvicorn main:admin_app --port 8001 --reload
admin_app = Starlette(debug=True)
admin = Admin(engine)
admin.add_view(ModelView(CMDBNetworkHost))
admin.add_view(ModelView(Events))
admin.add_view(ModelView(Incidents))

