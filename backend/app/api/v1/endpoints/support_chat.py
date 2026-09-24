import html
import logging
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.support_chat import SupportChatMessage, SupportChatSession
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas
class StartSessionRequest(BaseModel):
    id_card: str
    phone: str
    full_name: str


class SendMessageRequest(BaseModel):
    session_token: str
    content: str


class MessageOut(BaseModel):
    id: int
    sender_type: str
    content: str
    created_at: datetime


class SessionOut(BaseModel):
    session_token: str
    id_card: str
    phone: str
    full_name: str
    messages: list[MessageOut]


@router.post("/session", response_model=SessionOut)
async def get_or_create_session(data: StartSessionRequest, db: AsyncSession = Depends(get_db)):
    """
    Inicia o retoma una sesión de chat usando Cédula y Teléfono.
    Carga el historial previo de mensajes para que el usuario no pierda su conversación.
    """
    clean_id = data.id_card.strip().upper()
    clean_phone = data.phone.strip()
    clean_name = data.full_name.strip()

    if not clean_id or not clean_phone or not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cédula, teléfono y nombre son obligatorios."
        )

    # Buscar sesión existente por cédula
    stmt = (
        select(SupportChatSession)
        .where(SupportChatSession.id_card == clean_id)
        .options(selectinload(SupportChatSession.messages))
        .order_by(SupportChatSession.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if session:
        # Actualizar datos de contacto si cambiaron
        session.phone = clean_phone
        session.full_name = clean_name
        session.updated_at = datetime.utcnow()
    else:
        # Crear nueva sesión
        session = SupportChatSession(
            id_card=clean_id,
            phone=clean_phone,
            full_name=clean_name,
        )
        db.add(session)
        await db.flush()
        # Recargar mensajes vacíos
        await db.refresh(session, ["messages"])

    await db.commit()

    return SessionOut(
        session_token=session.session_token,
        id_card=session.id_card,
        phone=session.phone,
        full_name=session.full_name,
        messages=[
            MessageOut(
                id=m.id,
                sender_type=m.sender_type,
                content=m.content,
                created_at=m.created_at,
            )
            for m in (session.messages or [])
        ],
    )


@router.get("/session", response_model=SessionOut)
async def get_session_by_token(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Obtiene la sesión activa y su historial completo de mensajes a partir del token guardado en el navegador.
    """
    stmt = (
        select(SupportChatSession)
        .where(SupportChatSession.session_token == token.strip())
        .options(selectinload(SupportChatSession.messages))
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada.")

    return SessionOut(
        session_token=session.session_token,
        id_card=session.id_card,
        phone=session.phone,
        full_name=session.full_name,
        messages=[
            MessageOut(
                id=m.id,
                sender_type=m.sender_type,
                content=m.content,
                created_at=m.created_at,
            )
            for m in (session.messages or [])
        ],
    )


@router.post("/send", response_model=MessageOut)
async def send_visitor_message(data: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Envía un mensaje desde la web hacia el bot de Telegram del asesor.
    """
    clean_content = data.content.strip()
    if not clean_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El mensaje no puede estar vacío.")

    # Validar sesión
    stmt = select(SupportChatSession).where(SupportChatSession.session_token == data.session_token.strip())
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión inválida o expirada.")

    # Guardar mensaje en base de datos
    msg = SupportChatMessage(
        session_id=session.id,
        sender_type="visitor",
        content=clean_content,
    )
    db.add(msg)
    await db.flush()

    # Formatear y enviar mensaje a Telegram
    tg_text = (
        f"💬 <b>Nuevo mensaje de chat web</b>\n"
        f"👤 <b>Nombre:</b> {html.escape(session.full_name)}\n"
        f"🪪 <b>Cédula:</b> <code>{html.escape(session.id_card)}</code>\n"
        f"📱 <b>Teléfono:</b> <code>{html.escape(session.phone)}</code>\n"
        f"🆔 <b>Sesión:</b> #{session.id}\n\n"
        f"📝 <b>Mensaje:</b>\n"
        f"{html.escape(clean_content)}\n\n"
        f"<i>👉 Para responder al visitante, responde directamente a este mensaje en Telegram.</i>"
    )

    tg_msg_id = await telegram_service.send_message(tg_text)
    if tg_msg_id:
        msg.telegram_message_id = tg_msg_id

    await db.commit()
    await db.refresh(msg)

    return MessageOut(
        id=msg.id,
        sender_type=msg.sender_type,
        content=msg.content,
        created_at=msg.created_at,
    )


@router.get("/messages", response_model=list[MessageOut])
async def poll_messages(
    session_token: str = Query(...), 
    after_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Consulta mensajes nuevos para una sesión (utilizado por el polling en vivo del chat widget).
    """
    stmt = select(SupportChatSession.id).where(SupportChatSession.session_token == session_token.strip())
    res = await db.execute(stmt)
    session_id = res.scalar_one_or_none()

    if not session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada.")

    msg_query = (
        select(SupportChatMessage)
        .where(SupportChatMessage.session_id == session_id)
    )
    if after_id is not None:
        msg_query = msg_query.where(SupportChatMessage.id > after_id)

    msg_query = msg_query.order_by(SupportChatMessage.created_at.asc())
    msg_res = await db.execute(msg_query)
    messages = msg_res.scalars().all()

    return [
        MessageOut(
            id=m.id,
            sender_type=m.sender_type,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook donde Telegram envía las respuestas del asesor.
    Cuando el asesor responde (reply) a un mensaje, este webhook extrae la sesión y
    envía el mensaje al usuario en el chat web sin mezclar conversaciones.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    message = body.get("message")
    if not message:
        return {"status": "ignored", "reason": "no_message"}

    text = message.get("text", "").strip()
    if not text:
        return {"status": "ignored", "reason": "no_text"}

    reply_to = message.get("reply_to_message")
    if not reply_to:
        logger.info("Mensaje de Telegram recibido sin reply_to_message. No se puede enrutar a un usuario.")
        return {"status": "ignored", "reason": "not_a_reply"}

    reply_msg_id = reply_to.get("message_id")
    if not reply_msg_id:
        return {"status": "ignored", "reason": "missing_reply_msg_id"}

    # Buscar el mensaje original al que se respondió para saber la sesión
    stmt = (
        select(SupportChatMessage)
        .where(SupportChatMessage.telegram_message_id == reply_msg_id)
        .order_by(SupportChatMessage.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    orig_msg = res.scalar_one_or_none()

    if not orig_msg:
        # Fallback: intentar buscar por texto si contiene '#Sesión: #ID'
        reply_text = reply_to.get("text", "")
        import re
        match = re.search(r"Sesión:\s*#(\d+)", reply_text)
        if match:
            session_id = int(match.group(1))
        else:
            logger.warning("No se encontró mensaje o sesión vinculada a telegram_message_id %s", reply_msg_id)
            return {"status": "ignored", "reason": "session_not_found"}
    else:
        session_id = orig_msg.session_id

    # Guardar mensaje del asesor en la sesión del visitante
    agent_msg = SupportChatMessage(
        session_id=session_id,
        sender_type="agent",
        content=text,
        telegram_message_id=message.get("message_id"),
    )
    db.add(agent_msg)
    await db.commit()

    logger.info("Respuesta de Telegram vinculada exitosamente a sesión #%s", session_id)
    return {"status": "success", "session_id": session_id}
