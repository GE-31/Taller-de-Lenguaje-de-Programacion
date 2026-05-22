import json
import logging
import threading
import urllib.request
import urllib.error
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

_session_id_cache = None
_cache_lock = threading.Lock()


def _get_config():
    url = getattr(settings, 'OPENWA_URL', 'http://localhost:2785')
    api_key = getattr(settings, 'OPENWA_API_KEY', 'dev-admin-key')
    session_name = getattr(settings, 'OPENWA_SESSION_NAME', 'ventas')
    return url, api_key, session_name


def _resolver_session_id():
    global _session_id_cache
    with _cache_lock:
        if _session_id_cache:
            return _session_id_cache
        openwa_url, api_key, session_name = _get_config()
        try:
            req = urllib.request.Request(
                f'{openwa_url}/api/sessions',
                headers={'X-API-Key': api_key},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                sessions = json.loads(resp.read())
                for s in sessions:
                    if s.get('name') == session_name and s.get('status') == 'ready':
                        _session_id_cache = s['id']
                        return _session_id_cache
                logger.warning('OpenWA: sesión "%s" no encontrada o no está lista.', session_name)
        except Exception as exc:
            logger.error('OpenWA: no se pudo obtener la sesión: %s', exc)
    return None


def _normalizar_numero(telefono):
    digitos = ''.join(c for c in (telefono or '') if c.isdigit())
    if not digitos:
        return None
    if digitos.startswith('51') and len(digitos) == 11:
        return f'{digitos}@c.us'
    if len(digitos) == 9 and digitos.startswith('9'):
        return f'51{digitos}@c.us'
    if len(digitos) >= 10:
        return f'{digitos}@c.us'
    return None


def _construir_mensaje(boleto):
    origen = boleto.viaje.ruta.origen.title()
    destino = boleto.viaje.ruta.destino.title()
    fecha = boleto.viaje.fecha_salida.strftime('%d/%m/%Y a las %H:%M')
    comprobante = f'F001-{boleto.id:08d}'
    nombre = boleto.nombre_pasajero.title() or 'Pasajero'
    return (
        f'✅ *BOLETO CONFIRMADO - LINEA IMPERIAL*\n\n'
        f'Hola {nombre},\n'
        f'Tu pasaje ha sido confirmado exitosamente.\n\n'
        f'🚌 *Ruta:* {origen} → {destino}\n'
        f'📅 *Salida:* {fecha}\n'
        f'💺 *Asiento:* {boleto.numero_asiento}\n'
        f'🪪 *DNI:* {boleto.num_doc}\n'
        f'💰 *Precio:* S/ {boleto.precio_pagado}\n'
        f'📋 *Comprobante:* {comprobante}\n\n'
        f'Presenta este mensaje o tu DNI al abordar.\n'
        f'¡Buen viaje! 🙏'
    )


def _enviar_por_id(boleto_id):
    try:
        from apps.ventas.models import Boleto
        boleto = Boleto.objects.select_related(
            'viaje', 'viaje__ruta', 'viaje__bus', 'viaje__bus__empresa'
        ).get(id=boleto_id)
    except Exception as exc:
        logger.error('OpenWA: no se encontró boleto %s: %s', boleto_id, exc)
        return

    chat_id = _normalizar_numero(boleto.telefono_pasajero)
    if not chat_id:
        logger.warning('OpenWA: teléfono inválido en boleto %s ("%s")', boleto_id, boleto.telefono_pasajero)
        return

    session_id = _resolver_session_id()
    if not session_id:
        logger.error('OpenWA: no hay sesión activa, no se envió mensaje para boleto %s', boleto_id)
        return

    openwa_url, api_key, _ = _get_config()
    url = f'{openwa_url}/api/sessions/{session_id}/messages/send-text'
    payload = json.dumps({'chatId': chat_id, 'text': _construir_mensaje(boleto)}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'X-API-Key': api_key, 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info('OpenWA: mensaje enviado a %s (boleto %s, status %s)', chat_id, boleto_id, resp.status)
    except urllib.error.HTTPError as exc:
        logger.warning('OpenWA: error HTTP %s al enviar mensaje boleto %s: %s', exc.code, boleto_id, exc.read()[:200])
    except Exception as exc:
        logger.exception('OpenWA: error inesperado enviando mensaje boleto %s: %s', boleto_id, exc)


def enviar_confirmacion_boleto(boleto):
    boleto_id = boleto.id
    transaction.on_commit(
        lambda: threading.Thread(target=_enviar_por_id, args=(boleto_id,), daemon=True).start()
    )
