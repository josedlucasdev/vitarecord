import html
import logging
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
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


class RateSessionRequest(BaseModel):
    session_token: str
    rating: int  # 1 to 5
    comment: str | None = None


class MessageOut(BaseModel):
    id: int
    sender_type: str  # "visitor", "agent", "system"
    content: str
    created_at: datetime


class SessionOut(BaseModel):
    session_token: str
    id_card: str
    phone: str
    full_name: str
    status: str
    rating: int | None = None
    rating_comment: str | None = None
    messages: list[MessageOut]


@router.post("/session", response_model=SessionOut)
async def get_or_create_session(data: StartSessionRequest, db: AsyncSession = Depends(get_db)):
    """
    Inicia o retoma una sesión de chat usando Cédula y Teléfono.
    Carga el historial previo de mensajes para que el usuario no pierda su conversación.
    Si la conversación anterior ya fue finalizada y calificada, crea una nueva sesión.
    """
    clean_id = data.id_card.strip().upper()
    clean_phone = data.phone.strip()
    clean_name = data.full_name.strip()

    if not clean_id or not clean_phone or not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cédula, teléfono y nombre son obligatorios."
        )

    # Buscar última sesión existente por cédula
    stmt = (
        select(SupportChatSession)
        .where(SupportChatSession.id_card == clean_id)
        .options(selectinload(SupportChatSession.messages))
        .order_by(SupportChatSession.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    # Si la sesión anterior ya fue cerrada (calificada o no), crear una nueva sesión para nueva consulta
    if session and session.status == "closed":
        session = None

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
            status="active",
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
        status=session.status,
        rating=session.rating,
        rating_comment=session.rating_comment,
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
        status=session.status,
        rating=session.rating,
        rating_comment=session.rating_comment,
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

    if session.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Esta conversación ha sido finalizada. Por favor califica la atención o inicia una nueva consulta."
        )

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
        f"<i>👉 Para responder al visitante, responde directamente a este mensaje.</i>\n"
        f"<i>👉 Para finalizar la conversación y pedir calificación, responde: <code>/cerrar</code></i>"
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
    response: Response,
    session_token: str = Query(...), 
    after_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Consulta mensajes nuevos para una sesión (utilizado por el polling en vivo del chat widget).
    Retorna el estado de la sesión en los headers HTTP para que el cliente detecte el cierre.
    """
    stmt = select(SupportChatSession).where(SupportChatSession.session_token == session_token.strip())
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada.")

    response.headers["X-Session-Status"] = session.status
    response.headers["X-Session-Rated"] = "true" if session.rating is not None else "false"

    msg_query = (
        select(SupportChatMessage)
        .where(SupportChatMessage.session_id == session.id)
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


@router.post("/rate")
async def rate_support_chat(data: RateSessionRequest, db: AsyncSession = Depends(get_db)):
    """
    Registra la calificación (1 a 5 estrellas) y comentario del visitante sobre la atención,
    y notifica inmediatamente al administrador en Telegram.
    """
    if data.rating < 0 or data.rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La calificación debe estar entre 0 y 5 estrellas.")

    stmt = select(SupportChatSession).where(SupportChatSession.session_token == data.session_token.strip())
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada.")

    session.rating = data.rating
    session.rating_comment = data.comment.strip() if data.comment else None
    session.status = "closed"
    if not session.closed_at:
        session.closed_at = datetime.utcnow()

    if data.rating == 0:
        sys_msg = SupportChatMessage(
            session_id=session.id,
            sender_type="system",
            content="Conversación cerrada por el usuario sin calificar.",
        )
        db.add(sys_msg)
        await db.commit()

        tg_text = (
            f"ℹ️ <b>Conversación #{session.id} Finalizada</b>\n\n"
            f"👤 <b>Usuario:</b> {html.escape(session.full_name)}\n"
            f"🪪 <b>Cédula:</b> <code>{html.escape(session.id_card)}</code>\n"
            f"📱 <b>Teléfono:</b> <code>{html.escape(session.phone)}</code>\n\n"
            f"<i>El usuario decidió cerrar la conversación sin calificar.</i>"
        )
        await telegram_service.send_message(tg_text)
        return {"status": "success", "rating": 0, "comment": None}

    stars = "⭐" * data.rating
    sys_content = f"Has calificado la atención con {stars} ({data.rating}/5)."
    if session.rating_comment:
        sys_content += f"\nComentario: \"{session.rating_comment}\""

    sys_msg = SupportChatMessage(
        session_id=session.id,
        sender_type="system",
        content=sys_content,
    )
    db.add(sys_msg)
    await db.commit()

    # Enviar notificación a Telegram
    tg_text = (
        f"🌟 <b>¡Nueva Calificación de Atención Recibida!</b>\n\n"
        f"👤 <b>Usuario:</b> {html.escape(session.full_name)}\n"
        f"🪪 <b>Cédula:</b> <code>{html.escape(session.id_card)}</code>\n"
        f"📱 <b>Teléfono:</b> <code>{html.escape(session.phone)}</code>\n"
        f"🆔 <b>Sesión:</b> #{session.id}\n\n"
        f"⭐ <b>Puntuación:</b> {stars} (<b>{data.rating}/5</b>)\n"
    )
    if session.rating_comment:
        tg_text += f"💬 <b>Comentario:</b>\n<i>\"{html.escape(session.rating_comment)}\"</i>"
    else:
        tg_text += f"💬 <b>Comentario:</b> <i>(Sin comentario adicional)</i>"

    await telegram_service.send_message(tg_text)

    return {"status": "success", "rating": data.rating, "comment": session.rating_comment}


@router.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook donde Telegram envía las respuestas del asesor.
    - Si el asesor responde con /cerrar, /terminar o /finalizar:
      Finaliza la sesión en el chat web y le solicita la calificación al usuario.
    - Si es un mensaje normal:
      Lo envía al visitante en tiempo real.
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

    # Obtener sesión
    session_stmt = select(SupportChatSession).where(SupportChatSession.id == session_id)
    session_res = await db.execute(session_stmt)
    session = session_res.scalar_one_or_none()

    if not session:
        return {"status": "ignored", "reason": "session_not_found"}

    # Detectar si el asesor está cerrando la conversación
    text_lower = text.lower()
    close_keywords = ["/cerrar", "/terminar", "/finalizar", "/close", "/fin"]
    is_close_cmd = any(text_lower.startswith(k) for k in close_keywords)

    if is_close_cmd:
        # Extraer nota de despedida personalizada si la escribió
        parts = text.split(maxsplit=1)
        custom_farewell = parts[1].strip() if len(parts) > 1 else ""
        system_content = (
            custom_farewell if custom_farewell 
            else "El asesor ha dado por terminada la conversación. Por favor, califica la atención recibida."
        )

        session.status = "closed"
        session.closed_at = datetime.utcnow()

        close_msg = SupportChatMessage(
            session_id=session.id,
            sender_type="system",
            content=system_content,
            telegram_message_id=message.get("message_id"),
        )
        db.add(close_msg)
        await db.commit()

        # Confirmar al asesor en Telegram
        reply_tg_text = (
            f"✅ <b>Conversación finalizada con éxito</b>\n"
            f"👤 <b>Usuario:</b> {html.escape(session.full_name)} (#{session.id})\n"
            f"Se ha solicitado la calificación de atención al usuario en su pantalla de chat."
        )
        await telegram_service.send_message(
            reply_tg_text,
            reply_to_message_id=message.get("message_id")
        )
        return {"status": "session_closed", "session_id": session_id}

    # Mensaje normal del asesor
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
