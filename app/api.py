from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import r  # noqa: F401  (reexportado: conexão Redis compartilhada)
from app.routers.busca.routers import router as busca
from app.routers.cadastro_empresas.routers import router as cadastro_empresas
from app.routers.documentos.routers import router as documentos
from app.routers.empresas.routers import router as empresas
from app.routers.lotes.routers import router as lotes
from app.routers.revisao.routers import router as revisao
from app.routers.saude.routers import router as saude

app = FastAPI(title="Document AI Factory")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (saude, lotes, busca, documentos, revisao, empresas, cadastro_empresas):
    app.include_router(router)
