# app/routers/contacto.py
"""
Enrutador de Soporte Técnico y Contacto Público.

"""

import logging
from fastapi import APIRouter, HTTPException, Request, status

from app.core.email import send_support_email, send_user_support_confirmation
from app.core.logging import EmailRenderer
from app.schemas.contacto import ContactRequest, ContactResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CONTROLADOR DE RUTA 
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    summary="Envía una consulta desde el chatbot al equipo de soporte interno.",
)
def contact_support(payload: ContactRequest) -> ContactResponse:
    """
    Recibe la consulta de un usuario desde el AutoBot de la pantalla de login.
    
    Orquesta el envío del ticket de soporte hacia el inbox de asesores y despacha 
    un acuse de recibo automático (en proceso) al remitente de forma tolerante a fallos.
    """
    # 1. Despacho del ticket crítico al equipo de soporte (Operación Mandatoria)
    try:
        send_support_email(
            sender_email=payload.sender_email,
            subject=payload.subject,
            body=payload.message,
        )
        logger.info("[Support] Ticket de soporte recibido exitosamente de: %s", EmailRenderer.mask_email(payload.sender_email))
    except Exception as exc:
        logger.error("[Support] Error crítico enviando consulta de soporte al inbox: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible procesar tu solicitud de soporte en este momento. Inténtalo más tarde."
        )

    # 2. Despacho del acuse de recibo al usuario (Operación Complementaria / Tolerante a fallos)
    try:
        send_user_support_confirmation(
            to_email=payload.sender_email,
            subject_consulta=payload.subject,
        )
    except Exception as exc:
        # Fallo seguro controlado: Si falla la confirmación, NO le arruinamos el flujo al cliente,
        # puesto que el ticket para el asesor ya se guardó/envió con éxito.
        logger.warning(
            "[Support] El ticket se envió, pero falló el envío del acuse de recibo automático a %s: %s",
            EmailRenderer.mask_email(payload.sender_email), 
            str(exc)
        )

    return ContactResponse(
        ok=True, 
        detail="Tu consulta ha sido enviada con éxito. Nuestro equipo te responderá a la brevedad."
    )