"""
Script Utilitario de Diagnóstico para la API AutoManager.

Verifica de forma automatizada que el endpoint de soporte del chatbot esté 
correctamente inyectado en el árbol de rutas de FastAPI con el método HTTP idóneo.

"""

import os
import sys

# Asegura de forma dinámica que el directorio raíz del proyecto esté en el PATH de ejecución
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


def ejecutar_diagnostico_rutas() -> None:
    """
    Inspecciona el árbol de enrutamiento de la aplicación FastAPI.
    
    Valida la existencia del endpoint crítico de soporte y sus verbos HTTP.
    Termina la ejecución con códigos de estado del sistema (sys.exit) para 
    permitir automatizaciones en pipelines de CI/CD.
    """
    print("🔍 Iniciando diagnóstico de infraestructura de enrutamiento...")
    print("═" * 70)

    try:
        # Importación tardía controlada para capturar fallos de inicialización del core
        from main import app
        
        target_path = "/api/support/contact"
        target_method = "POST"
        endpoint_encontrado = False

        # Mapeo completo y estructurado de rutas registradas en la aplicación principal
        for route in app.routes:
            # Atributo 'methods' contiene el set de verbos HTTP permitidos (GET, POST, etc.)
            methods_allowed = getattr(route, "methods", set())
            
            # Verificación elástica de ruta y método exacto
            if route.path == target_path and target_method in methods_allowed:
                endpoint_encontrado = True
                break

        if endpoint_encontrado:
            print(f"✅ [ÉXITO] El endpoint crítico está operativo: {target_method} {target_path}")
            print("═" * 70)
            sys.exit(0)  # Salida exitosa estándar del sistema (Código 0)
        
        else:
            print(f"❌ [FALLO] Endpoint NO registrado o método incorrecto: Esperado {target_method} {target_path}")
            print("\n📋 Rutas y métodos detectados actualmente en la API:")
            
            # Formateo estructurado y ordenado alfabéticamente para facilitar la depuración
            for route in sorted(app.routes, key=lambda x: x.path):
                methods = list(getattr(route, "methods", []))
                # Filtramos middlewares internos que no exponen endpoints de cara al cliente
                if methods:
                    print(f"   👉 {methods} → {route.path}")
            
            print("═" * 70)
            sys.exit(1)  # Salida con error estándar del sistema (Código 1)

    except ImportError as e:
        print(f"❌ [FALLO CRÍTICO] Error de importación en main.py o en su cadena de dependencias.")
        print(f"    Detalle técnico del sistema: {str(e)}")
        print("💡 Verifica que tu entorno virtual (.venv) esté activo y las librerías instaladas.")
        print("═" * 70)
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ [ERROR INESPERADO] Falla de inicialización general: {str(e)}")
        print("═" * 70)
        sys.exit(1)


if __name__ == "__main__":
    ejecutar_diagnostico_rutas()