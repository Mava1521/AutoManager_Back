"""
Punto de Entrada Principal de la API AutoManager.

Configura el ciclo de vida de la aplicación, levanta los esquemas de la base 
de datos, inyecta las dependencias globales (CORS, Middlewares) y mapea los 
enrutadores (routers) de los módulos del sistema.

"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import LoggingMiddleware, setup_logging
from app.db.database import engine
from app.db import models
from app.routers import auth, vehiculos, contacto
from seed import run_seed


# ══════════════════════════════════════════════════════════════════════════════
# GESTIÓN DEL CICLO DE VIDA 
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Controla los eventos de arranque (startup) y apagado (shutdown) de la API.
    
    Asegura que la infraestructura de base de datos y logs esté lista antes de 
    empezar a escuchar peticiones HTTP de los clientes.
    """
    # ── Ejecuciones en el Arranque (Startup) ──
    
    # 1. Inicializar los manejadores de logs profesionales refactorizados
    setup_logging()
    
    # 2. Generar esquemas relacionales en la base de datos si no existen
    models.Base.metadata.create_all(bind=engine)
    
    # 3. Insertar registros iniciales (Semillas) de forma segura si la BD está vacía
    run_seed()

    # Cede el control a la aplicación para procesar peticiones HTTP en runtime
    yield 
    
    # ── Ejecuciones en el Apagado (Shutdown) ──
    # Espacio para liberar conexiones a bases de datos o brokers si fuera necesario
    pass


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA APLICACIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AutoManager API",
    description="Backend para el sistema de gestión de vehículos — Monitoring Innovation",
    version="1.0.0",
    lifespan=lifespan  # Inyección del gestor de ciclo de vida
)

# ── MIDDLEWARES GLOBALES ──────────────────────────────────────────────────────

# CORS — Restringe o habilita peticiones cruzadas desde el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://auto-manager-front.vercel.app", # Tu URL de Vercel sin diagonal al final
        "http://localhost:5173"                  # Para desarrollo local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auditoría y Métricas — Interceptor avanzado de tráfico HTTP refactorizado
app.add_middleware(LoggingMiddleware)


# ── REGISTRO DE RUTAS (Routers Modularizados) ─────────────────────────────────

app.include_router(auth.router,      prefix="/api/auth",     tags=["Auth"])
app.include_router(vehiculos.router, prefix="/api/vehiculos", tags=["Vehiculos"])
app.include_router(contacto.router,  prefix="/api/support",  tags=["Support"])


# ── ENDPOINTS DE INFRAESTRUCTURA ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """
    Verificación de Disponibilidad (Health Check).
    
    Utilizado por herramientas de monitoreo y orquestadores en la nube 
    (Render, Railway, AWS) para validar de manera rápida si la app está en línea.
    """
    return {
        "status": "ok", 
        "app": app.title, 
        "version": app.version
    }