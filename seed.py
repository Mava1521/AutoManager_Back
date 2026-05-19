"""
Script de Poblamiento de Base de Datos Inicial (Database Seeding).

Garantiza la creación de esquemas relacionales e inyecta un juego de datos 
idempotente (usuarios con roles RBAC diferenciados y vehículos de prueba) 
para acelerar el aprovisionamiento de entornos de desarrollo local y staging.
"""

import sys
import logging
from app.db.database import SessionLocal, engine
from app.db.models import Base, Usuario, Vehiculo, RolEnum, StatusEnum
from app.core.security import hash_password

# Configuración básica de logs para terminal
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_seed() -> None:
    """
    Ejecuta el proceso transaccional de seeding aplicando principios de idempotencia
    independiente por cada modelo de datos del ecosistema AutoManager.
    """
    print("\n🌱 Iniciando aprovisionamiento de datos iniciales...")
    print("═" * 70)

    # 1. Uso de Context Manager para asegurar el ciclo de vida de la sesión de BD
    with SessionLocal() as db:
        try:
            # ══════════════════════════════════════════════════════════════════
            # SEED DE USUARIOS (Roles: Admin y Viewer)
            # ══════════════════════════════════════════════════════════════════
            if db.query(Usuario).count() == 0:
                print("👤 Creando cuentas de usuario base (RBAC)...")
                
                usuarios = [
                    Usuario(
                        nombre="Admin",
                        apellido="Manager",
                        email="admin@automanager.com",
                        password=hash_password("Admin1234!"),
                        rol=RolEnum.admin,
                    ),
                    Usuario(
                        nombre="David",
                        apellido="Sandoval",
                        email="david@automanager.com",
                        password=hash_password("Viewer1234!"),
                        rol=RolEnum.viewer,
                    )
                ]
                db.add_all(usuarios)
                db.flush()  # Sincroniza los cambios con la sesión sin confirmar la transacción aún
                print("   ✅ Usuarios inyectados con éxito.")
            else:
                print("ℹ️  La tabla de usuarios ya contiene registros. Omitiendo seed de credenciales.")

            # ══════════════════════════════════════════════════════════════════
            # SEED DE VEHÍCULOS (Datos de Negocio para el Dashboard)
            # ══════════════════════════════════════════════════════════════════
            if db.query(Vehiculo).count() == 0:
                print("\n🚗 Generando inventario demostrativo de vehículos...")
                
                vehiculos_ejemplo = [
                    Vehiculo(marca="Mazda", sucursal="Chapinero", aspirante="David Sandoval", status=StatusEnum.APROBADO),
                    Vehiculo(marca="Mercedes", sucursal="Santa Fe", aspirante="Ana Rodríguez", status=StatusEnum.EN_REVISION),
                    Vehiculo(marca="Ford", sucursal="Teusaquillo", aspirante="Carlos López", status=StatusEnum.PENDIENTE),
                    Vehiculo(marca="Renault", sucursal="Chapinero", aspirante="María García", status=StatusEnum.APROBADO),
                    Vehiculo(marca="Chevrolet", sucursal="Barrios Unidos", aspirante="Juan Pérez", status=StatusEnum.RECHAZADO),
                    Vehiculo(marca="Volkswagen", sucursal="Chapinero", aspirante="Laura Martínez", status=StatusEnum.EN_REVISION),
                    Vehiculo(marca="Suzuki", sucursal="Santa Fe", aspirante="Pedro Sánchez", status=StatusEnum.PENDIENTE),
                    Vehiculo(marca="KIA", sucursal="Teusaquillo", aspirante="Sofía Ramírez", status=StatusEnum.APROBADO),
                    Vehiculo(marca="Hyundai", sucursal="Chapinero", aspirante="Javier Torres", status=StatusEnum.EN_REVISION),
                    Vehiculo(marca="Honda", sucursal="Barrios Unidos", aspirante="Valentina Castro", status=StatusEnum.PENDIENTE),
                    Vehiculo(marca="Volvo", sucursal="Santa Fe", aspirante="Andrés Herrera", status=StatusEnum.APROBADO),
                    Vehiculo(marca="BMW", sucursal="Chapinero", aspirante="Carolina Díaz", status=StatusEnum.RECHAZADO),
                ]
                db.add_all(vehiculos_ejemplo)
                db.flush()
                print(f"   ✅ {len(vehiculos_ejemplo)} vehículos inyectados con éxito.")
            else:
                print("ℹ️  La tabla de vehículos ya contiene registros. Omitiendo seed de negocio.")

            # 2. Consolidación atómica de la transacción entera
            db.commit()
            
            print("\n🏁 [PROCESO COMPLETADO] Datos listos para autenticación:")
            print("═" * 70)
            print("   🔑 CREDENCIALES DE ACCESO DE PRUEBA:")
            print("   • Rol ADMINISTRADOR:")
            print("     Usuario: admin@automanager.com  | Contraseña: Admin1234!")
            print("   • Rol VISUALIZADOR (Viewer):")
            print("     Usuario: david@automanager.com  | Contraseña: Viewer1234!")
            print("═" * 70)

        except Exception as exc:
            db.rollback()
            logger.error("\n❌ Error transaccional abortando el proceso de seed: %s", str(exc))
            sys.exit(1)


if __name__ == "__main__":
    # Asegura de forma mandatoria la existencia previa de las tablas físicas en la BD antes de insertar
    Base.metadata.create_all(bind=engine)
    run_seed()