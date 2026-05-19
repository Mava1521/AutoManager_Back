# app/routers/vehiculos.py
"""
Enrutador de Operaciones sobre Vehículos (Módulo Central de Negocio).

"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Vehiculo, Usuario
from app.schemas.vehiculo import VehiculoCreate, VehiculoUpdate, VehiculoOut
from app.dependencies import get_current_user, require_admin

router = APIRouter()
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ADICIÓN DE ESQUEMAS DECLARATIVOS 
# ══════════════════════════════════════════════════════════════════════════════

class BulkDeleteRequest(BaseModel):
    """Esquema de validación estricta para la eliminación masiva de registros."""
    ids: List[int] = Field(..., min_items=1, description="Lista de identificadores únicos a eliminar.")


class BulkDeleteResponse(BaseModel):
    """Estructura de respuesta formal de la API para confirmación de bajas."""
    deleted: int
    ids: List[int]


# ══════════════════════════════════════════════════════════════════════════════
# SERVICIO DE SOPORTE TRANSACCIONAL 
# ══════════════════════════════════════════════════════════════════════════════

class VehiculoService:
    """Encapsula los flujos operativos y el ciclo de vida transaccional de los vehículos."""

    @staticmethod
    def get_by_id_or_404(db: Session, vehiculo_id: int) -> Vehiculo:
        """Busca una entidad por ID o lanza una excepción HTTP 404 estandarizada."""
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
        if not vehiculo:
            logger.warning("[VehiculoService] Intento de consulta en ID inexistente: %d", vehiculo_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehículo con id={vehiculo_id} no encontrado."
            )
        return vehiculo


# ══════════════════════════════════════════════════════════════════════════════
# CONTROLADORES DE RUTA 
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[VehiculoOut], summary="Lista la totalidad de los vehículos registrados.")
def list_vehiculos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> List[Vehiculo]:
    """Retorna el inventario completo de vehículos sin restricciones de filtrado."""
    return db.query(Vehiculo).all()


@router.get("/{vehiculo_id}", response_model=VehiculoOut, summary="Obtiene el detalle completo de un vehículo.")
def get_vehiculo(
    vehiculo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Vehiculo:
    """Retorna los metadatos de un vehículo específico validando su existencia previa."""
    return VehiculoService.get_by_id_or_404(db, vehiculo_id)


@router.post("/", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED, summary="Registra un nuevo vehículo.")
def create_vehiculo(
    payload: VehiculoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
) -> Vehiculo:
    """Inserta un nuevo vehículo en el sistema. Operación restringida a Administradores."""
    nuevo_vehiculo = Vehiculo(**payload.model_dump())
    try:
        db.add(nuevo_vehiculo)
        db.commit()
        db.refresh(nuevo_vehiculo)
        logger.info("[Vehiculos] Vehículo creado con éxito. ID: %d", nuevo_vehiculo.id)
        return nuevo_vehiculo
    except Exception as exc:
        db.rollback()
        logger.error("[Vehiculos] Falla al persistir el registro del vehículo: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al guardar el vehículo en la base de datos."
        )


@router.put("/{vehiculo_id}", response_model=VehiculoOut, summary="Actualiza parcial o totalmente un vehículo.")
def update_vehiculo(
    vehiculo_id: int,
    payload: VehiculoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
) -> Vehiculo:
    """Modifica de forma reactiva los campos del vehículo. Operación restringida a Administradores."""
    vehiculo = VehiculoService.get_by_id_or_404(db, vehiculo_id)
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehiculo, field, value)
    
    try:
        db.commit()
        db.refresh(vehiculo)
        logger.info("[Vehiculos] Vehículo ID %d actualizado exitosamente.", vehiculo.id)
        return vehiculo
    except Exception as exc:
        db.rollback()
        logger.error("[Vehiculos] Error al actualizar la entidad ID %d: %s", vehiculo_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible consolidar la actualización de los datos."
        )


@router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Elimina físicamente un vehículo.")
def delete_vehiculo(
    vehiculo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
) -> None:
    """Remueve de manera permanente un vehículo del sistema. Operación restringida a Administradores."""
    vehiculo = VehiculoService.get_by_id_or_404(db, vehiculo_id)
    try:
        db.delete(vehiculo)
        db.commit()
        logger.info("[Vehiculos] Vehículo ID %d eliminado físicamente.", vehiculo_id)
    except Exception as exc:
        db.rollback()
        logger.error("[Vehiculos] Error al intentar eliminar la entidad ID %d: %s", vehiculo_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fallo de infraestructura al procesar la baja del vehículo."
        )


@router.get("/unique/marcas", response_model=List[str], summary="Extrae el catálogo de marcas sin duplicados.")
def get_unique_marcas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> List[str]:
    """Obtiene una lista compacta de todas las marcas registradas para alimentar filtros en la UI."""
    marcas = db.query(Vehiculo.marca).distinct().all()
    return [m[0] for m in marcas if m[0]]


@router.get("/unique/sucursales", response_model=List[str], summary="Extrae el catálogo de sucursales sin duplicados.")
def get_unique_sucursales(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> List[str]:
    """Obtiene una lista de todas las sucursales del sistema para alimentar controles de UI."""
    sucursales = db.query(Vehiculo.sucursal).distinct().all()
    return [s[0] for s in sucursales if s[0]]


@router.post("/bulk-delete", response_model=BulkDeleteResponse, status_code=status.HTTP_200_OK, summary="Elimina de forma masiva múltiples registros.")
def bulk_delete_vehiculos(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Procesa de manera atómica la remoción de múltiples vehículos mediante un lote de IDs.
    
    Operación crítica restringida al rol Administrador. Ejecuta un borrado masivo 
    directo optimizando las transacciones por red.
    """
    try:
        deleted_count = db.query(Vehiculo).filter(Vehiculo.id.in_(payload.ids)).delete(synchronize_session=False)
        db.commit()
        logger.info("[Vehiculos - Bulk] Eliminación en lote procesada. Removidos: %d registros.", deleted_count)
        return {"deleted": deleted_count, "ids": payload.ids}
    except Exception as exc:
        db.rollback()
        logger.error("[Vehiculos - Bulk] Falla transaccional durante el borrado masivo: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo completar la eliminación masiva debido a un conflicto en la base de datos."
        )