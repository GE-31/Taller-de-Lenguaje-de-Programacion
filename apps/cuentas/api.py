import json
import re
from datetime import date
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Pasajero


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: BUSCAR PASAJERO POR DNI
# ══════════════════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def buscar_pasajero_por_dni(request):
    """
    Busca un pasajero por DNI y retorna sus datos de forma segura.
    
    ENDPOINT: GET /api/pasajeros/buscar-por-dni/?dni=71852009
    
    RESPONSE (si existe):
    {
        "existe": true,
        "id": 1,
        "dni": "71852009",
        "nombres": "Juan",
        "apellidos": "Pérez",
        "genero": "M",
        "fecha_nacimiento": "1990-05-15",
        "telefono": "967271XXX",         ← OCULTO (últimos 3 dígitos)
        "correo": "jua****@gmail.com"    ← OCULTO (primeros 3 caracteres visibles)
    }

    RESPONSE (si no existe):
    {
        "existe": false
    }
    
    NOTAS DE SEGURIDAD:
    - Devuelve datos parcialmente ocultos si no está autenticado
    - El DNI debe tener exactamente 8 dígitos
    - Usa índice en base de datos para búsqueda rápida
    """
    dni = request.GET.get('dni', '').strip()

    # Validar DNI
    if not dni:
        return JsonResponse(
            {'error': 'El DNI es obligatorio'},
            status=400
        )

    if not re.match(r'^\d{8}$', dni):
        return JsonResponse(
            {'error': 'El DNI debe tener exactamente 8 dígitos'},
            status=400
        )

    try:
        pasajero = Pasajero.objects.get(dni=dni)
        
        # Retornar datos con información sensible parcialmente oculta
        return JsonResponse(
            pasajero.to_dict(incluir_completos=False),
            status=200
        )
    except Pasajero.DoesNotExist:
        return JsonResponse({'existe': False}, status=200)
    except Exception:
        return JsonResponse(
            {'error': 'Error interno al buscar pasajero'},
            status=500
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: GUARDAR O ACTUALIZAR PASAJERO
# ══════════════════════════════════════════════════════════════════════════════

@require_http_methods(["POST"])
def guardar_actualizar_pasajero(request):
    """
    Guarda o actualiza un pasajero en la base de datos.
    
    ENDPOINT: POST /api/pasajeros/guardar/
    
    REQUEST BODY:
    {
        "dni": "71852009",
        "nombres": "Juan",
        "apellidos": "Pérez",
        "genero": "M",
        "fecha_nacimiento": "1990-05-15",
        "telefono": "967271234",
        "correo": "juan@gmail.com"
    }

    RESPONSE (201 si es nuevo, 200 si es actualización):
    {
        "id": 1,
        "dni": "71852009",
        "nombres": "Juan",
        "apellidos": "Pérez",
        "genero": "M",
        "fecha_nacimiento": "1990-05-15",
        "telefono": "967271XXX",
        "correo": "jua****@gmail.com",
        "creado": true,          ← true si es nuevo, false si fue actualizado
        "actualizado": false
    }
    
    ERRORES POSIBLES:
    - 400: JSON inválido, DNI vacío, campos obligatorios faltantes
    - 409: Validación fallida
    - 500: Error interno del servidor
    
    VALIDACIONES:
    - DNI: obligatorio, 8 dígitos numéricos
    - Nombres: obligatorio, min 2 caracteres
    - Apellidos: obligatorio, min 2 caracteres
    - Email: formato válido (si se proporciona)
    - Teléfono: formato numérico (si se proporciona)
    """
    try:
        # Parsear JSON del request
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'JSON inválido. Verifica el formato.'},
            status=400
        )

    # ─────────────────────────────────────────────────────────────────────────
    # VALIDAR DATOS REQUERIDOS
    # ─────────────────────────────────────────────────────────────────────────

    dni = datos.get('dni', '').strip()
    if not dni:
        return JsonResponse(
            {'error': 'El DNI es obligatorio'},
            status=400
        )

    # Validar formato de DNI
    if not re.match(r'^\d{8}$', dni):
        return JsonResponse(
            {'error': 'El DNI debe tener exactamente 8 dígitos'},
            status=400
        )

    # Validar nombres
    nombres = datos.get('nombres', '').strip()
    if not nombres:
        return JsonResponse(
            {'error': 'Los nombres son obligatorios'},
            status=400
        )

    if len(nombres) < 2 or len(nombres) > 150:
        return JsonResponse(
            {'error': 'Los nombres deben tener entre 2 y 150 caracteres'},
            status=400
        )

    # Validar apellidos
    apellidos = datos.get('apellidos', '').strip()
    if not apellidos:
        return JsonResponse(
            {'error': 'Los apellidos son obligatorios'},
            status=400
        )

    if len(apellidos) < 2 or len(apellidos) > 150:
        return JsonResponse(
            {'error': 'Los apellidos deben tener entre 2 y 150 caracteres'},
            status=400
        )

    # ─────────────────────────────────────────────────────────────────────────
    # VALIDAR DATOS OPCIONALES
    # ─────────────────────────────────────────────────────────────────────────

    telefono = datos.get('telefono')
    if telefono is not None:
        telefono = str(telefono).strip()
        if telefono and not re.match(r'^\d{9}$', telefono):
            return JsonResponse(
                {'error': 'El teléfono debe tener exactamente 9 dígitos'},
                status=400
            )

    correo = datos.get('correo')
    if correo is not None:
        correo = str(correo).strip().lower()
        # Validar email con expresión regular simple
        patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if correo and not re.match(patron_email, correo):
            return JsonResponse(
                {'error': 'El correo electrónico no es válido'},
                status=400
            )

    genero = datos.get('genero', 'M').strip()
    if genero not in ['M', 'F', 'O']:
        return JsonResponse(
            {'error': 'El género debe ser M, F u O'},
            status=400
        )

    fecha_nacimiento = datos.get('fecha_nacimiento')
    if fecha_nacimiento == '':
        fecha_nacimiento = None
    elif fecha_nacimiento:
        try:
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento)
        except ValueError:
            return JsonResponse(
                {'error': 'La fecha de nacimiento no es valida'},
                status=400
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GUARDAR O ACTUALIZAR EN BASE DE DATOS
    # ─────────────────────────────────────────────────────────────────────────

    try:
        defaults = {
            'nombres': nombres,
            'apellidos': apellidos,
            'genero': genero,
            'fecha_nacimiento': fecha_nacimiento,
        }
        if telefono is not None:
            defaults['telefono'] = telefono
        if correo is not None:
            defaults['correo'] = correo

        with transaction.atomic():
            pasajero, creado = Pasajero.objects.update_or_create(
                dni=dni,
                defaults=defaults,
            )

        # Preparar respuesta
        respuesta = pasajero.to_dict(incluir_completos=False)
        respuesta['creado'] = creado
        respuesta['actualizado'] = not creado

        # Usar status 201 si es nuevo, 200 si fue actualizado
        status_code = 201 if creado else 200

        return JsonResponse(respuesta, status=status_code)

    except ValidationError as e:
        return JsonResponse(
            {'error': str(e)},
            status=409
        )
    except Exception as e:
        print(f'Error al guardar pasajero: {str(e)}')
        return JsonResponse(
            {'error': 'Error interno al guardar pasajero'},
            status=500
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT: OBTENER PASAJERO POR ID (ADMIN ONLY)
# ══════════════════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def obtener_pasajero(request, pasajero_id):
    """
    Obtiene los datos completos de un pasajero por ID.
    
    ENDPOINT: GET /api/pasajeros/{id}/
    
    RESPUESTA:
    {
        "id": 1,
        "dni": "71852009",
        "nombres": "Juan",
        "apellidos": "Pérez",
        "genero": "M",
        "fecha_nacimiento": "1990-05-15",
        "telefono": "967271234",        ← COMPLETO (sin ocultar)
        "correo": "juan@gmail.com",     ← COMPLETO (sin ocultar)
        "existe": true
    }
    
    NOTAS:
    - Devuelve datos completos (sin ocultar datos sensibles)
    - Requiere usuario staff autenticado
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse(
            {'error': 'No autorizado'},
            status=403
        )

    try:
        pasajero = Pasajero.objects.get(id=pasajero_id)
        return JsonResponse(
            pasajero.to_dict(incluir_completos=True),
            status=200
        )
    except Pasajero.DoesNotExist:
        return JsonResponse(
            {'error': 'Pasajero no encontrado'},
            status=404
        )
    except Exception:
        return JsonResponse(
            {'error': 'Error interno al obtener pasajero'},
            status=500
        )
