import json
import re
import time as time_module
from datetime import date, datetime, time

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Asiento,
    Compra,
    DetalleConfiteria,
    Entrada,
    Funcion,
    Pelicula,
    ProductoConfiteria,
    Sala,
)

# Constantes de catálogo para formularios del panel
GENEROS = ["Acción", "Animación", "Aventura", "Ciencia ficción", "Comedia", "Drama", "Romance", "Suspenso", "Terror"]
CLASIFICACIONES = ["TE", "+7", "+10", "+14", "+18"]
IDIOMAS = ["Doblada", "Subtitulada"]
FORMATOS = ["2D", "3D"]
ESTADOS_PELICULA = [("proximo", "Próximo estreno"), ("en_cartelera", "En cartelera"), ("fuera", "Fuera de cartelera")]
CATEGORIAS = ["Combos", "Cabritas", "Bebidas", "Dulces"]
TIPOS_CUENTA = ["Cliente", "Administrador"]
PRECIOS_BASE = {"general": 5500, "estudiante": 4500, "adulto_mayor": 4000}
SECCIONES_CON_FORMULARIO = ["peliculas", "funciones", "salas", "productos", "usuarios", "caja"]
TIEMPO_RESERVA_SEGUNDOS = 600  # 10 minutos


# ---------------------------- Helpers internos ----------------------------

def _clp(n):
    """Formato chileno: 9900 -> $9.900"""
    return "$" + format(int(n or 0), ",").replace(",", ".")


def _asegurar_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _cache_key_reservas(funcion_id):
    return f"reservas_funcion_{funcion_id}"


def _obtener_reservas_funcion(funcion_id):
    """Devuelve las reservas temporales vigentes (no expiradas) para una función."""
    ahora = time_module.time()
    actuales = cache.get(_cache_key_reservas(funcion_id)) or {}
    vigentes = {
        int(aid): info
        for aid, info in actuales.items()
        if info.get("expira_ts", 0) > ahora
    }
    if len(vigentes) != len(actuales):
        cache.set(_cache_key_reservas(funcion_id), vigentes, timeout=TIEMPO_RESERVA_SEGUNDOS)
    return vigentes


def _reservar_asientos_temporalmente(funcion, asientos_objs, session_key):
    """Reserva asientos por 10 minutos para session_key si no están ocupados ni reservados por otro."""
    ocupados_bd = set(
        Entrada.objects.filter(funcion=funcion, asiento__in=asientos_objs).values_list("asiento_id", flat=True)
    )
    if ocupados_bd:
        raise ValidationError("Uno o más asientos seleccionados ya fueron comprados. Elige otros.")

    reservas = _obtener_reservas_funcion(funcion.id)
    for a in asientos_objs:
        info = reservas.get(a.id)
        if info and info.get("session_key") != session_key:
            raise ValidationError(f"El asiento {a.codigo} está reservado temporalmente por otro cliente.")

    # Limpiar reservas previas de esta misma sesión en esta función y registrar las nuevas
    reservas = {
        aid: info for aid, info in reservas.items() if info.get("session_key") != session_key
    }
    expira_ts = time_module.time() + TIEMPO_RESERVA_SEGUNDOS
    for a in asientos_objs:
        reservas[a.id] = {
            "session_key": session_key,
            "expira_ts": expira_ts,
            "codigo": a.codigo,
        }
    cache.set(_cache_key_reservas(funcion.id), reservas, timeout=TIEMPO_RESERVA_SEGUNDOS)
    return expira_ts


def _liberar_reserva_temporal(funcion_id, session_key):
    if not funcion_id or not session_key:
        return
    reservas = _obtener_reservas_funcion(funcion_id)
    nuevas = {
        aid: info for aid, info in reservas.items() if info.get("session_key") != session_key
    }
    cache.set(_cache_key_reservas(funcion_id), nuevas, timeout=TIEMPO_RESERVA_SEGUNDOS)


def _segundos_restantes_reserva(request):
    datos = request.session.get("compra_en_curso") or {}
    expira_ts = datos.get("expira_ts")
    if not expira_ts:
        return TIEMPO_RESERVA_SEGUNDOS
    restante = int(expira_ts - time_module.time())
    return max(0, min(TIEMPO_RESERVA_SEGUNDOS, restante))


def _asegurar_asientos_sala(sala, filas=8, por_fila=12):
    """Garantiza que la sala tenga asientos creados en la base de datos."""
    if sala.asientos.exists():
        return
    nuevos = []
    for i in range(filas):
        letra = chr(ord("A") + i)
        for n in range(1, por_fila + 1):
            nuevos.append(Asiento(sala=sala, fila=letra, numero=n))
    Asiento.objects.bulk_create(nuevos, ignore_conflicts=True)


def _precios_funcion(funcion):
    precio_general = int(funcion.precio)
    if precio_general == PRECIOS_BASE["general"]:
        return dict(PRECIOS_BASE)
    return {
        "general": precio_general,
        "estudiante": max(0, round(precio_general * 0.82 / 100) * 100),
        "adulto_mayor": max(0, round(precio_general * 0.73 / 100) * 100),
    }


def _construir_mapa_sala(funcion, session_key=None):
    _asegurar_asientos_sala(funcion.sala)
    asientos_qs = list(funcion.sala.asientos.order_by("fila", "numero"))
    ocupados_ids = set(
        Entrada.objects.filter(funcion=funcion).values_list("asiento_id", flat=True)
    )
    reservas_temp = _obtener_reservas_funcion(funcion.id)

    por_fila = {}
    for a in asientos_qs:
        por_fila.setdefault(a.fila, []).append(a)

    letras = sorted(por_fila.keys())
    ultima_fila = letras[-1] if letras else ""
    filas = []
    for letra in letras:
        lista = por_fila[letra]
        max_num = max((a.numero for a in lista), default=12)
        asientos_fila = []
        for a in lista:
            reserva_info = reservas_temp.get(a.id)
            reservado_por_otro = bool(
                reserva_info and reserva_info.get("session_key") != session_key
            )
            seleccionado_por_mi = bool(
                session_key and reserva_info and reserva_info.get("session_key") == session_key
            )

            if a.id in ocupados_ids:
                estado = "ocupado"
            elif reservado_por_otro:
                estado = "reservado"
            elif letra == ultima_fila and max_num >= 4 and a.numero in (1, 2, max_num - 1, max_num):
                estado = "movilidad"
            else:
                estado = "disponible"

            asientos_fila.append({
                "id": a.id,
                "codigo": a.codigo,
                "fila": a.fila,
                "numero": a.numero,
                "estado": estado,
                "ocupado": a.id in ocupados_ids,
                "reservado": reservado_por_otro,
                "seleccionado": seleccionado_por_mi,
                "pasillo": max_num >= 4 and a.numero == max_num // 2,
            })
        filas.append({"letra": letra, "asientos": asientos_fila})
    return filas


def _resolver_asientos_sala(sala, identificadores):
    """Recibe códigos ('D5') o IDs (15) y devuelve la lista de objetos Asiento de la sala."""
    _asegurar_asientos_sala(sala)
    asientos_sala = list(sala.asientos.all())
    por_codigo = {f"{a.fila}{a.numero}".upper(): a for a in asientos_sala}
    por_id = {a.id: a for a in asientos_sala}

    encontrados = []
    vistos = set()
    for item in identificadores:
        asiento = None
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            asiento = por_id.get(int(item))
        if asiento is None and isinstance(item, str):
            asiento = por_codigo.get(item.strip().upper())
        if asiento is None:
            raise ValidationError(f"El asiento '{item}' no existe en {sala.nombre_sala}.")
        if asiento.id not in vistos:
            vistos.add(asiento.id)
            encontrados.append(asiento)
    return encontrados


def _combinar_fecha_hora(fecha_str, hora_str):
    fecha_obj = parse_date(str(fecha_str)) if not isinstance(fecha_str, date) else fecha_str
    if not fecha_obj:
        raise ValidationError("Fecha inválida.")
    try:
        partes = [int(p) for p in str(hora_str).strip().split(":")]
        hora_obj = time(partes[0], partes[1] if len(partes) > 1 else 0)
    except (ValueError, IndexError):
        raise ValidationError("Hora inválida.")
    dt = datetime.combine(fecha_obj, hora_obj)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _resumen_compra_sesion(request):
    datos = request.session.get("compra_en_curso") or {}
    funcion = None
    if datos.get("funcion_id"):
        funcion = Funcion.objects.select_related("pelicula", "sala").filter(pk=datos["funcion_id"]).first()

    pelicula_nombre = funcion.pelicula.nombre if funcion else "Solo confitería"
    funcion_texto = f"{funcion.sala.nombre_sala} · {funcion.hora}" if funcion else "—"
    asientos_codigos = datos.get("asientos_codigos") or []
    asientos_texto = ", ".join(asientos_codigos) if asientos_codigos else "—"
    subtotal_entradas = int(datos.get("subtotal_entradas") or 0)

    productos_map = datos.get("productos") or {}
    subtotal_confiteria = 0
    if productos_map:
        ids = [int(pid) for pid in productos_map.keys() if str(pid).isdigit()]
        for prod in ProductoConfiteria.objects.filter(id__in=ids, disponible=True):
            cant = int(productos_map.get(str(prod.id), 0))
            if cant > 0:
                subtotal_confiteria += cant * prod.precio_unitario

    return {
        "pelicula": pelicula_nombre,
        "funcion": funcion_texto,
        "asientos": asientos_texto,
        "base": subtotal_entradas,
        "entradas": subtotal_entradas,
        "confiteria": subtotal_confiteria,
        "total": subtotal_entradas + subtotal_confiteria,
    }


def _obtener_o_crear_usuario_compra(request, correo=""):
    if request.user.is_authenticated:
        return request.user
    usuario_modelo = get_user_model()
    correo = (correo or "").strip()
    if correo:
        existente = usuario_modelo.objects.filter(
            Q(email__iexact=correo) | Q(username__iexact=correo)
        ).first()
        if existente:
            return existente
        usuario = usuario_modelo(username=correo[:150], email=correo)
        usuario.set_unusable_password()
        usuario.save()
        return usuario
    invitado, _ = usuario_modelo.objects.get_or_create(
        username="invitado@cinenido.cl",
        defaults={"email": "invitado@cinenido.cl", "first_name": "Cliente"},
    )
    return invitado


# ---------------------------- Público ----------------------------

def cartelera(request):
    q = request.GET.get("q", "").strip()
    peliculas_qs = Pelicula.objects.filter(activa=True).order_by("fecha_estreno", "nombre")
    if q:
        peliculas_qs = peliculas_qs.filter(
            Q(nombre__icontains=q)
            | Q(director__icontains=q)
            | Q(sinopsis__icontains=q)
            | Q(clasificacion__icontains=q)
        )
    peliculas = list(peliculas_qs)
    return render(request, "cine_nido/cartelera.html", {
        "q": q,
        "en_cartelera": [p for p in peliculas if p.estado == "en_cartelera"],
        "proximos": [p for p in peliculas if p.estado == "proximo"],
    })


def pelicula_detalle(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, pk=pelicula_id)
    funciones_qs = pelicula.funciones.select_related("sala").order_by("fecha_hora")
    dias_map = {}
    for f in funciones_qs:
        dias_map.setdefault(f.fecha, []).append(f)
    dias = [{"fecha": d, "funciones": dias_map[d]} for d in sorted(dias_map.keys())]
    return render(request, "cine_nido/pelicula_detalle.html", {
        "pelicula": pelicula,
        "dias": dias,
    })


# ---------------------------- Compra (5 pasos) ----------------------------

def asientos(request, funcion_id):
    funcion = get_object_or_404(
        Funcion.objects.select_related("pelicula", "sala"),
        pk=funcion_id,
    )
    session_key = _asegurar_session_key(request)
    request.session["funcion_id_actual"] = funcion.id
    return render(request, "cine_nido/asientos.html", {
        "funcion": funcion,
        "pelicula": funcion.pelicula,
        "mapa": _construir_mapa_sala(funcion, session_key=session_key),
        "precios": _precios_funcion(funcion),
        "segundos_restantes": _segundos_restantes_reserva(request),
    })


def compra_correo(request):
    datos = dict(request.session.get("compra_en_curso") or {})
    if not datos.get("asientos_ids") and not datos.get("productos"):
        messages.error(request, "Selecciona primero una función y tus asientos.")
        return redirect("cartelera")

    # Si el usuario ya inició sesión, usamos su correo registrado automáticamente
    if request.user.is_authenticated:
        datos["correo"] = request.user.email or request.user.username
        request.session["compra_en_curso"] = datos
        return redirect("confiteria")

    correo = datos.get("correo", "")
    if request.method == "POST":
        correo = request.POST.get("correo", "").strip()
        destino = request.POST.get("destino", "confiteria")
        try:
            validate_email(correo)
        except ValidationError:
            messages.error(request, "Ingresa un correo electrónico válido para enviar tus entradas.")
        else:
            datos["correo"] = correo
            request.session["compra_en_curso"] = datos
            if destino == "pago":
                return redirect("pago")
            return redirect("confiteria")

    return render(request, "cine_nido/correo_compra.html", {
        "correo": correo,
        "funcion_id": datos.get("funcion_id"),
        "resumen": _resumen_compra_sesion(request),
        "segundos_restantes": _segundos_restantes_reserva(request),
    })


def confiteria(request):
    if request.method == "POST":
        funcion_id = request.POST.get("funcion_id") or request.session.get("funcion_id_actual")
        if not funcion_id:
            messages.error(request, "Selecciona primero una función.")
            return redirect("cartelera")

        funcion = get_object_or_404(
            Funcion.objects.select_related("pelicula", "sala"),
            pk=funcion_id,
        )
        codigos = request.POST.getlist("asientos")
        tipo_entrada = request.POST.get("tipo_entrada", "general")

        if not codigos:
            messages.error(request, "Debes elegir al menos un asiento.")
            return redirect("asientos", funcion_id=funcion.id)

        session_key = _asegurar_session_key(request)
        try:
            asientos_objs = _resolver_asientos_sala(funcion.sala, codigos)
            expira_ts = _reservar_asientos_temporalmente(funcion, asientos_objs, session_key)
        except ValidationError as err:
            messages.error(request, err.messages[0])
            return redirect("asientos", funcion_id=funcion.id)

        precios = _precios_funcion(funcion)
        precio_unitario = precios.get(tipo_entrada, funcion.precio)
        correo_auto = (
            (request.user.email or request.user.username)
            if request.user.is_authenticated
            else ""
        )
        request.session["compra_en_curso"] = {
            "funcion_id": funcion.id,
            "asientos_ids": [a.id for a in asientos_objs],
            "asientos_codigos": [a.codigo for a in asientos_objs],
            "tipo_entrada": tipo_entrada,
            "precio_entrada": precio_unitario,
            "subtotal_entradas": precio_unitario * len(asientos_objs),
            "productos": {},
            "correo": correo_auto,
            "expira_ts": expira_ts,
        }

        # Si NO ha iniciado sesión, pedir correo antes de seguir al pago/confitería
        if not request.user.is_authenticated:
            return redirect("compra_correo")

    productos_qs = list(ProductoConfiteria.objects.filter(disponible=True).order_by("id"))
    categorias = []
    for cat in CATEGORIAS:
        prods = [p for p in productos_qs if p.categoria == cat]
        if prods:
            categorias.append({"nombre": cat, "slug": cat.lower(), "productos": prods})

    return render(request, "cine_nido/confiteria.html", {
        "categorias": categorias,
        "resumen": _resumen_compra_sesion(request),
    })


def pago(request):
    datos = dict(request.session.get("compra_en_curso") or {})
    if request.user.is_authenticated and not datos.get("correo"):
        datos["correo"] = request.user.email or request.user.username
        request.session["compra_en_curso"] = datos

    correo_compra = (
        (request.user.email or request.user.username)
        if request.user.is_authenticated
        else datos.get("correo", "")
    )

    if request.method == "POST":
        # Paso 3 -> Paso 4: viene desde el formulario de confitería
        if "confirmar_pago" not in request.POST and "medio" not in request.POST:
            productos_sel = {}
            for key, val in request.POST.items():
                if key.startswith("producto_"):
                    pid = key.split("_", 1)[1]
                    try:
                        cantidad = max(0, min(20, int(val or 0)))
                    except ValueError:
                        cantidad = 0
                    if pid.isdigit() and cantidad > 0:
                        productos_sel[pid] = cantidad
            datos["productos"] = productos_sel
            request.session["compra_en_curso"] = datos

            if not request.user.is_authenticated and not correo_compra:
                return redirect("compra_correo")

            return render(request, "cine_nido/pago.html", {
                "resumen": _resumen_compra_sesion(request),
                "correo_compra": correo_compra,
                "segundos_restantes": _segundos_restantes_reserva(request),
            })

        # Paso 4 -> Paso 5: confirmación de pago y creación de Compra en la BD
        asientos_ids = datos.get("asientos_ids") or []
        productos_map = datos.get("productos") or {}
        funcion_id = datos.get("funcion_id")

        if not asientos_ids and not productos_map:
            messages.error(request, "No hay elementos seleccionados para procesar la compra.")
            return redirect("cartelera")

        correo = (
            (request.user.email or request.user.username)
            if request.user.is_authenticated
            else (request.POST.get("correo", "").strip() or correo_compra)
        )
        if not request.user.is_authenticated and not correo:
            return redirect("compra_correo")

        usuario = _obtener_o_crear_usuario_compra(request, correo=correo)
        session_key = _asegurar_session_key(request)

        try:
            with transaction.atomic():
                compra = Compra.objects.create(usuario=usuario, total=0)
                total_compra = 0

                if funcion_id and asientos_ids:
                    funcion = get_object_or_404(Funcion, pk=funcion_id)
                    asientos_objs = list(
                        Asiento.objects.filter(id__in=asientos_ids, sala=funcion.sala)
                    )
                    if len(asientos_objs) != len(asientos_ids):
                        raise ValidationError("Los asientos seleccionados no pertenecen a la sala de la función.")

                    if Entrada.objects.select_for_update().filter(
                        funcion=funcion, asiento__in=asientos_objs
                    ).exists():
                        raise ValidationError("Uno o más asientos seleccionados acaban de ser ocupados.")

                    reservas_temp = _obtener_reservas_funcion(funcion.id)
                    for asiento in asientos_objs:
                        r_info = reservas_temp.get(asiento.id)
                        if r_info and r_info.get("session_key") != session_key:
                            raise ValidationError(f"El asiento {asiento.codigo} está reservado por otro cliente.")

                    precio_entrada = int(datos.get("precio_entrada") or funcion.precio)
                    for asiento in asientos_objs:
                        Entrada.objects.create(
                            compra=compra,
                            funcion=funcion,
                            asiento=asiento,
                            precio=precio_entrada,
                        )
                        total_compra += precio_entrada

                if productos_map:
                    ids_prod = [int(pid) for pid in productos_map.keys() if str(pid).isdigit()]
                    productos_bd = {
                        p.id: p for p in ProductoConfiteria.objects.filter(id__in=ids_prod, disponible=True)
                    }
                    for pid_str, cant in productos_map.items():
                        prod = productos_bd.get(int(pid_str))
                        cant_int = int(cant or 0)
                        if prod and cant_int > 0:
                            DetalleConfiteria.objects.create(
                                compra=compra,
                                producto_confiteria=prod,
                                cantidad=cant_int,
                                precio_unitario=prod.precio_unitario,
                            )
                            total_compra += cant_int * prod.precio_unitario

                compra.total = total_compra
                compra.save(update_fields=["total"])
        except (ValidationError, IntegrityError) as err:
            mensaje = err.messages[0] if hasattr(err, "messages") and err.messages else "No se pudo completar la compra."
            messages.error(request, mensaje)
            if funcion_id:
                return redirect("asientos", funcion_id=funcion_id)
            return redirect("cartelera")

        _liberar_reserva_temporal(funcion_id, session_key)
        request.session.pop("compra_en_curso", None)
        messages.success(request, "¡Tu compra se realizó exitosamente!")
        return redirect("entrada", compra_id=compra.id)

    if not request.user.is_authenticated and not correo_compra and (datos.get("asientos_ids") or datos.get("productos")):
        return redirect("compra_correo")

    return render(request, "cine_nido/pago.html", {
        "resumen": _resumen_compra_sesion(request),
        "correo_compra": correo_compra,
        "segundos_restantes": _segundos_restantes_reserva(request),
    })


def entrada(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("usuario").prefetch_related(
            "entradas__asiento",
            "entradas__funcion__pelicula",
            "entradas__funcion__sala",
            "detalles_confiteria__producto_confiteria",
        ),
        pk=compra_id,
    )
    return render(request, "cine_nido/entrada.html", {"compra": compra})


# ---------------------------- Cuenta ----------------------------

def ingresar(request):
    if request.user.is_authenticated:
        return redirect("cartelera")

    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST":
        correo = request.POST.get("correo", "").strip()
        clave = request.POST.get("clave", "")
        usuario_modelo = get_user_model()
        usuario = usuario_modelo.objects.filter(email__iexact=correo).first() if correo else None
        if usuario is None:
            usuario = authenticate(request, username=correo, password=clave)
        else:
            usuario = authenticate(request, username=usuario.get_username(), password=clave)

        if usuario is not None:
            login(request, usuario)
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("cartelera")

        messages.error(request, "El correo o la contraseña no son correctos.")

    return render(request, "cine_nido/ingresar.html", {
        "correo": request.POST.get("correo", ""),
        "next": next_url,
    })


def registro(request):
    if request.user.is_authenticated:
        return redirect("cartelera")

    datos = {
        "nombre": request.POST.get("nombre", "").strip(),
        "correo": request.POST.get("correo", "").strip(),
    }
    if request.method == "POST":
        correo = datos["correo"]
        nombre = datos["nombre"]
        clave = request.POST.get("clave", "")
        clave2 = request.POST.get("clave2", "")
        usuario_modelo = get_user_model()
        errores = []

        try:
            validate_email(correo)
        except ValidationError:
            errores.append("Ingresa un correo válido.")

        if not nombre:
            errores.append("Ingresa tu nombre.")
        if usuario_modelo.objects.filter(email__iexact=correo).exists():
            errores.append("Ya existe una cuenta con ese correo.")
        if clave != clave2:
            errores.append("Las contraseñas no coinciden.")

        partes_nombre = nombre.split(maxsplit=1)
        usuario = usuario_modelo(
            username=correo,
            email=correo,
            first_name=partes_nombre[0][:150],
            last_name=partes_nombre[1][:150] if len(partes_nombre) > 1 else "",
        )
        try:
            validate_password(clave, user=usuario)
        except ValidationError as error:
            errores.extend(error.messages)

        if len(correo) > 150:
            errores.append("El correo no puede superar los 150 caracteres.")
        if usuario_modelo.objects.filter(username__iexact=correo).exists():
            errores.append("No se puede usar ese correo para crear el nombre de usuario.")

        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            usuario = usuario_modelo.objects.create_user(
                username=correo,
                email=correo,
                password=clave,
                first_name=partes_nombre[0][:150],
                last_name=partes_nombre[1][:150] if len(partes_nombre) > 1 else "",
            )
            login(request, usuario)
            messages.success(request, "Tu cuenta fue creada correctamente.")
            return redirect("cartelera")

    return render(request, "cine_nido/registro.html", datos)


def salir(request):
    if request.method != "POST":
        return redirect("cartelera")
    logout(request)
    messages.success(request, "Has cerrado sesión.")
    return redirect("cartelera")


def recuperar(request):
    if request.method == "POST":
        correo = request.POST.get("correo", "").strip()
        if correo:
            messages.success(
                request,
                "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña.",
            )
            return redirect("ingresar")
    return render(request, "cine_nido/recuperar.html")


def mis_compras(request):
    if request.user.is_authenticated:
        compras = list(
            Compra.objects.filter(usuario=request.user).prefetch_related(
                "entradas__funcion__pelicula",
                "entradas__asiento",
            )
        )
    else:
        compras = []
    return render(request, "cine_nido/mis_compras.html", {"compras": compras})


# ---------------------------- Panel interno ----------------------------

def _construir_secciones_panel(request, q=""):
    q_clean = (q or "").strip()

    # Películas
    peliculas_qs = Pelicula.objects.all().order_by("-activa", "nombre")
    if q_clean:
        peliculas_qs = peliculas_qs.filter(
            Q(nombre__icontains=q_clean) | Q(director__icontains=q_clean) | Q(clasificacion__icontains=q_clean)
        )
    filas_peliculas = []
    for p in peliculas_qs:
        if not p.activa:
            badge = {"texto": "Fuera de cartelera", "badge": "error"}
        elif p.estado == "proximo":
            badge = {"texto": "Próximo estreno", "badge": "info"}
        else:
            badge = {"texto": "En cartelera", "badge": "ok"}
        filas_peliculas.append({
            "pk": p.pk,
            "celdas": [p.nombre, p.director, f"{p.duracion} min", p.clasificacion, badge],
        })

    # Funciones
    funciones_qs = Funcion.objects.select_related("pelicula", "sala").annotate(
        vendidas_count=Count("entradas")
    ).order_by("fecha_hora")
    if q_clean:
        funciones_qs = funciones_qs.filter(
            Q(pelicula__nombre__icontains=q_clean) | Q(sala__nombre_sala__icontains=q_clean)
        )
    filas_funciones = []
    for f in funciones_qs:
        capacidad = f.sala.capacidad
        filas_funciones.append({
            "pk": f.pk,
            "celdas": [
                f.pelicula.nombre,
                f.sala.nombre_sala,
                f.fecha.strftime("%d/%m/%Y"),
                f.hora,
                f"{f.vendidas_count} / {capacidad}",
            ],
        })

    # Salas
    salas_qs = Sala.objects.all().order_by("nombre_sala")
    if q_clean:
        salas_qs = salas_qs.filter(nombre_sala__icontains=q_clean)
    filas_salas = [
        {
            "pk": s.pk,
            "celdas": [
                s.nombre_sala,
                s.capacidad,
                s.filas,
                s.accesibles,
                {"texto": "Activa", "badge": "ok"},
            ],
        }
        for s in salas_qs
    ]

    # Productos de confitería
    productos_qs = ProductoConfiteria.objects.all().order_by("id")
    if q_clean:
        productos_qs = productos_qs.filter(nombre__icontains=q_clean)
    filas_productos = [
        {
            "pk": p.pk,
            "celdas": [
                p.nombre,
                p.categoria,
                _clp(p.precio_unitario),
                {"texto": "Disponible", "badge": "ok"}
                if p.disponible
                else {"texto": "No disponible", "badge": "error"},
            ],
        }
        for p in productos_qs
    ]

    # Ventas (Compras)
    compras_qs = Compra.objects.select_related("usuario").prefetch_related(
        "entradas__funcion__pelicula"
    ).order_by("-fecha_compra")
    if q_clean:
        compras_qs = compras_qs.filter(
            Q(usuario__email__icontains=q_clean)
            | Q(usuario__username__icontains=q_clean)
            | Q(entradas__funcion__pelicula__nombre__icontains=q_clean)
        ).distinct()
    filas_ventas = [
        {
            "pk": c.pk,
            "celdas": [
                c.numero,
                c.fecha_compra.strftime("%d/%m/%Y"),
                c.pelicula,
                c.canal,
                _clp(c.total),
                c.estado,
            ],
        }
        for c in compras_qs
    ]

    # Usuarios
    usuario_modelo = get_user_model()
    usuarios_qs = usuario_modelo.objects.all().order_by("id")
    if q_clean:
        usuarios_qs = usuarios_qs.filter(
            Q(username__icontains=q_clean)
            | Q(email__icontains=q_clean)
            | Q(first_name__icontains=q_clean)
            | Q(last_name__icontains=q_clean)
        )
    filas_usuarios = [
        {
            "pk": u.pk,
            "celdas": [
                f"{u.first_name} {u.last_name}".strip() or u.username,
                u.email or u.username,
                "Administrador" if u.is_staff else "Cliente",
                {"texto": "Activo", "badge": "ok"}
                if u.is_active
                else {"texto": "Inactivo", "badge": "error"},
            ],
        }
        for u in usuarios_qs
    ]

    # Caja (sesión + total de ventas reales)
    total_ventas_bd = Compra.objects.aggregate(s=Sum("total"))["s"] or 0
    cajas = request.session.get("cajas_panel") or [
        {
            "id": 1,
            "turno": "Turno actual",
            "usuario": request.user.get_full_name() or request.user.username if request.user.is_authenticated else "Administrador",
            "punto": "Boletería",
            "inicial": 30000,
            "efectivo": total_ventas_bd,
            "tarjeta": 0,
            "contado": 30000 + total_ventas_bd,
        }
    ]
    filas_caja = []
    for c in cajas:
        dif = int(c["contado"]) - int(c["inicial"]) - int(c["efectivo"])
        filas_caja.append({
            "pk": c["id"],
            "celdas": [
                c["turno"],
                c["usuario"],
                _clp(c["inicial"]),
                _clp(int(c["efectivo"]) + int(c["tarjeta"])),
                {
                    "texto": _clp(dif).replace("$-", "-$"),
                    "badge": "ok" if dif == 0 else "error",
                },
            ],
        })

    return {
        "peliculas": {
            "titulo": "Películas",
            "nuevo": "Nueva película",
            "columnas": ["Título", "Director", "Duración", "Clasificación", "Estado"],
            "filas": filas_peliculas,
        },
        "funciones": {
            "titulo": "Funciones",
            "nuevo": "Nueva función",
            "columnas": ["Película", "Sala", "Fecha", "Hora", "Vendidas"],
            "filas": filas_funciones,
        },
        "salas": {
            "titulo": "Salas",
            "nuevo": "Nueva sala",
            "columnas": ["Sala", "Capacidad", "Filas", "Asientos accesibles", "Estado"],
            "filas": filas_salas,
        },
        "productos": {
            "titulo": "Productos de confitería",
            "nuevo": "Nuevo producto",
            "columnas": ["Producto", "Categoría", "Precio", "Disponibilidad"],
            "filas": filas_productos,
        },
        "ventas": {
            "titulo": "Ventas",
            "nuevo": None,
            "columnas": ["N° venta", "Fecha", "Película", "Canal", "Total", "Estado"],
            "filas": filas_ventas,
        },
        "usuarios": {
            "titulo": "Usuarios",
            "nuevo": "Nuevo usuario",
            "columnas": ["Nombre", "Correo", "Tipo de cuenta", "Estado"],
            "filas": filas_usuarios,
        },
        "caja": {
            "titulo": "Caja (apertura y cierre)",
            "nuevo": "Abrir caja",
            "columnas": ["Turno", "Responsable", "Monto inicial", "Ventas", "Diferencia"],
            "filas": filas_caja,
        },
        "reportes": {
            "titulo": "Reportes",
            "nuevo": None,
            "columnas": ["Reporte", "Período", "Formato"],
            "filas": [
                {"pk": 1, "celdas": ["Ventas de entradas", "Último mes", "PDF / Excel"]},
                {"pk": 2, "celdas": ["Ventas de confitería", "Último mes", "PDF / Excel"]},
                {"pk": 3, "celdas": ["Ocupación por sala", "Última semana", "PDF / Excel"]},
            ],
        },
    }


def _panel(request, seccion_activa, extra=None, q=""):
    secciones = _construir_secciones_panel(request, q=q)
    ctx = {"seccion_activa": seccion_activa, "secciones": secciones}
    ctx.update(extra or {})
    return ctx


def panel_dashboard(request):
    total_ventas = Compra.objects.aggregate(s=Sum("total"))["s"] or 0
    entradas_vendidas = Entrada.objects.count()
    total_funciones = Funcion.objects.count()
    total_asientos_programados = sum(f.sala.capacidad for f in Funcion.objects.select_related("sala"))
    ocupacion = round((entradas_vendidas / total_asientos_programados) * 100) if total_asientos_programados else 0
    inactivos = list(ProductoConfiteria.objects.filter(disponible=False))

    proximas = [
        {
            "pelicula": f.pelicula.nombre,
            "sala": f.sala.nombre_sala,
            "hora": f.hora,
        }
        for f in Funcion.objects.select_related("pelicula", "sala").order_by("fecha_hora")[:5]
    ]
    return render(request, "cine_nido/panel/dashboard.html", _panel(request, "dashboard", {
        "proximas": proximas,
        "kpis": {
            "ventas_hoy": _clp(total_ventas),
            "entradas_vendidas": entradas_vendidas,
            "ocupacion": f"{ocupacion}%",
            "no_disponibles": len(inactivos),
        },
        "alertas_stock": inactivos,
    }))


def panel_listado(request, seccion):
    q = request.GET.get("q", "").strip()
    secciones = _construir_secciones_panel(request, q=q)
    datos = secciones.get(seccion)
    if not datos:
        raise Http404("Sección no encontrada")
    return render(request, "cine_nido/panel/listado.html", {
        "seccion_activa": seccion,
        "secciones": secciones,
        "datos": datos,
        "tiene_formulario": seccion in SECCIONES_CON_FORMULARIO,
    })


def panel_formulario(request, seccion, pk=None):
    secciones = _construir_secciones_panel(request)
    datos = secciones.get(seccion)
    if not datos or seccion not in SECCIONES_CON_FORMULARIO:
        raise Http404("Sección sin formulario")

    usuario_modelo = get_user_model()
    obj = None
    if pk is not None:
        if seccion == "peliculas":
            obj = get_object_or_404(Pelicula, pk=pk)
        elif seccion == "funciones":
            obj = get_object_or_404(Funcion.objects.select_related("pelicula", "sala"), pk=pk)
        elif seccion == "salas":
            obj = get_object_or_404(Sala, pk=pk)
        elif seccion == "productos":
            obj = get_object_or_404(ProductoConfiteria, pk=pk)
        elif seccion == "usuarios":
            u = get_object_or_404(usuario_modelo, pk=pk)
            obj = {
                "id": u.pk,
                "instancia": u,
                "nombre": f"{u.first_name} {u.last_name}".strip() or u.username,
                "rut": "",
                "telefono": "",
                "correo": u.email or u.username,
                "tipo_cuenta": "Administrador" if u.is_staff else "Cliente",
                "activo": u.is_active,
            }
        elif seccion == "caja":
            cajas = request.session.get("cajas_panel") or [
                {
                    "id": 1,
                    "turno": "Turno actual",
                    "usuario": request.user.username if request.user.is_authenticated else "Administrador",
                    "punto": "Boletería",
                    "inicial": 30000,
                    "efectivo": Compra.objects.aggregate(s=Sum("total"))["s"] or 0,
                    "tarjeta": 0,
                    "contado": 30000 + (Compra.objects.aggregate(s=Sum("total"))["s"] or 0),
                }
            ]
            obj = next((c for c in cajas if c["id"] == pk), cajas[0] if cajas else None)
            if obj is None:
                raise Http404("Caja no encontrada")

    if request.method == "POST":
        accion = request.POST.get("accion")

        # Dar de baja / eliminar
        if accion == "baja" and pk is not None:
            if seccion == "peliculas":
                obj.activa = False
                obj.save(update_fields=["activa"])
                messages.warning(request, f"La película '{obj.nombre}' fue dada de baja de la cartelera.")
            elif seccion == "funciones":
                try:
                    obj.delete()
                    messages.warning(request, "La función fue cancelada correctamente.")
                except ProtectedError:
                    messages.error(request, "No se puede eliminar una función que ya tiene entradas vendidas.")
            elif seccion == "salas":
                try:
                    obj.delete()
                    messages.warning(request, "La sala fue eliminada correctamente.")
                except ProtectedError:
                    messages.error(request, "No se puede dar de baja una sala con funciones o entradas asociadas.")
            elif seccion == "productos":
                obj.disponible = False
                obj.save(update_fields=["disponible"])
                messages.warning(request, f"El producto '{obj.nombre}' fue marcado como no disponible.")
            elif seccion == "usuarios":
                u = obj["instancia"]
                u.is_active = False
                u.save(update_fields=["is_active"])
                messages.warning(request, f"El usuario '{u.username}' fue dado de baja.")
            return redirect("panel_listado", seccion)

        # Guardar / Crear
        try:
            if seccion == "peliculas":
                nombre = request.POST.get("nombre", "").strip()
                director = request.POST.get("director", "").strip() or "Por confirmar"
                sinopsis = request.POST.get("sinopsis", "").strip()
                duracion = max(1, int(request.POST.get("duracion") or 90))
                clasificacion = request.POST.get("clasificacion", "TE").strip()
                fecha_estreno = parse_date(request.POST.get("fecha_estreno", "")) or timezone.localdate()
                portada = request.POST.get("portada", "").strip() or None
                estado_val = request.POST.get("estado", "en_cartelera")
                activa = estado_val != "fuera"

                if not nombre:
                    raise ValidationError("El título de la película es obligatorio.")

                if obj is None:
                    Pelicula.objects.create(
                        nombre=nombre,
                        director=director,
                        sinopsis=sinopsis,
                        duracion=duracion,
                        clasificacion=clasificacion,
                        fecha_estreno=fecha_estreno,
                        portada=portada,
                        activa=activa,
                    )
                    messages.success(request, "Película agregada correctamente.")
                else:
                    obj.nombre = nombre
                    obj.director = director
                    obj.sinopsis = sinopsis
                    obj.duracion = duracion
                    obj.clasificacion = clasificacion
                    obj.fecha_estreno = fecha_estreno
                    obj.portada = portada
                    obj.activa = activa
                    obj.save()
                    messages.success(request, "Película actualizada correctamente.")

            elif seccion == "funciones":
                pelicula_id = request.POST.get("pelicula")
                sala_val = request.POST.get("sala", "").strip()
                fecha_str = request.POST.get("fecha", "")
                hora_str = request.POST.get("hora", "")
                precio = max(0, int(request.POST.get("precio_general") or request.POST.get("precio") or PRECIOS_BASE["general"]))

                pelicula_obj = get_object_or_404(Pelicula, pk=pelicula_id)
                if sala_val.isdigit():
                    sala_obj = get_object_or_404(Sala, pk=int(sala_val))
                else:
                    sala_obj = get_object_or_404(Sala, nombre_sala=sala_val)

                fecha_hora = _combinar_fecha_hora(fecha_str, hora_str)
                conflicto = Funcion.objects.filter(sala=sala_obj, fecha_hora=fecha_hora)
                if obj is not None:
                    conflicto = conflicto.exclude(pk=obj.pk)
                if conflicto.exists():
                    raise ValidationError("Ya existe una función programada en esa sala y horario.")

                if obj is None:
                    Funcion.objects.create(
                        pelicula=pelicula_obj,
                        sala=sala_obj,
                        fecha_hora=fecha_hora,
                        precio=precio,
                    )
                    messages.success(request, "Función programada correctamente.")
                else:
                    obj.pelicula = pelicula_obj
                    obj.sala = sala_obj
                    obj.fecha_hora = fecha_hora
                    obj.precio = precio
                    obj.save()
                    messages.success(request, "Función actualizada correctamente.")

            elif seccion == "salas":
                nombre_sala = request.POST.get("nombre", "").strip()
                filas_num = max(1, min(20, int(request.POST.get("filas") or 8)))
                por_fila_num = max(1, min(24, int(request.POST.get("por_fila") or 12)))
                if not nombre_sala:
                    raise ValidationError("El nombre de la sala es obligatorio.")

                if obj is None:
                    sala_nueva = Sala.objects.create(nombre_sala=nombre_sala)
                    _asegurar_asientos_sala(sala_nueva, filas=filas_num, por_fila=por_fila_num)
                    messages.success(request, f"Sala '{nombre_sala}' creada con {filas_num * por_fila_num} asientos.")
                else:
                    obj.nombre_sala = nombre_sala
                    obj.save()
                    _asegurar_asientos_sala(obj, filas=filas_num, por_fila=por_fila_num)
                    messages.success(request, f"Sala '{nombre_sala}' actualizada correctamente.")

            elif seccion == "productos":
                nombre = request.POST.get("nombre", "").strip()
                precio = max(0, int(request.POST.get("precio") or 0))
                foto = request.POST.get("foto", "").strip() or None
                if not nombre:
                    raise ValidationError("El nombre del producto es obligatorio.")

                if obj is None:
                    ProductoConfiteria.objects.create(
                        nombre=nombre,
                        precio_unitario=precio,
                        foto=foto,
                        disponible=True,
                    )
                    messages.success(request, "Producto agregado a confitería.")
                else:
                    obj.nombre = nombre
                    obj.precio_unitario = precio
                    obj.foto = foto
                    obj.disponible = True
                    obj.save()
                    messages.success(request, "Producto actualizado correctamente.")

            elif seccion == "usuarios":
                nombre = request.POST.get("nombre", "").strip()
                correo = request.POST.get("correo", "").strip()
                tipo_cuenta = request.POST.get("tipo_cuenta", "Cliente")
                es_staff = tipo_cuenta == "Administrador"
                partes = nombre.split(maxsplit=1)
                first_name = partes[0][:150] if partes else ""
                last_name = partes[1][:150] if len(partes) > 1 else ""

                if obj is None:
                    clave = request.POST.get("clave", "")
                    clave2 = request.POST.get("clave2", "")
                    if clave != clave2:
                        raise ValidationError("Las contraseñas no coinciden.")
                    if usuario_modelo.objects.filter(Q(email__iexact=correo) | Q(username__iexact=correo)).exists():
                        raise ValidationError("Ya existe un usuario con ese correo.")
                    nuevo = usuario_modelo.objects.create_user(
                        username=correo,
                        email=correo,
                        password=clave,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    nuevo.is_staff = es_staff
                    nuevo.save(update_fields=["is_staff"])
                    messages.success(request, "Usuario creado correctamente.")
                else:
                    u = obj["instancia"]
                    u.first_name = first_name
                    u.last_name = last_name
                    u.email = correo
                    u.username = correo[:150]
                    u.is_staff = es_staff
                    u.save()
                    messages.success(request, "Usuario actualizado correctamente.")

            elif seccion == "caja":
                cajas = list(request.session.get("cajas_panel") or [])
                if obj is None:
                    responsable = request.POST.get("responsable", "Administrador").strip()
                    punto = request.POST.get("punto", "Boletería")
                    inicial = max(0, int(request.POST.get("inicial") or 0))
                    efectivo = Compra.objects.aggregate(s=Sum("total"))["s"] or 0
                    nuevo_id = max((c["id"] for c in cajas), default=0) + 1
                    cajas.append({
                        "id": nuevo_id,
                        "turno": f"Turno #{nuevo_id}",
                        "usuario": responsable,
                        "punto": punto,
                        "inicial": inicial,
                        "efectivo": efectivo,
                        "tarjeta": 0,
                        "contado": inicial + efectivo,
                    })
                    request.session["cajas_panel"] = cajas
                    messages.success(request, "Caja abierta correctamente.")
                else:
                    contado = max(0, int(request.POST.get("contado") or 0))
                    for c in cajas:
                        if c["id"] == obj["id"]:
                            c["contado"] = contado
                    if not cajas:
                        obj["contado"] = contado
                        cajas = [obj]
                    request.session["cajas_panel"] = cajas
                    messages.success(request, "Cierre de caja registrado correctamente.")

            return redirect("panel_listado", seccion)
        except (ValidationError, IntegrityError, ValueError) as err:
            mensaje = err.messages[0] if hasattr(err, "messages") and err.messages else str(err)
            messages.error(request, mensaje)

    extra = {"datos": datos, "obj": obj, "editando": pk is not None, "pk": pk}
    if seccion == "peliculas":
        extra.update(
            generos=GENEROS,
            clasificaciones=CLASIFICACIONES,
            idiomas=IDIOMAS,
            formatos=FORMATOS,
            estados=ESTADOS_PELICULA,
        )
    elif seccion == "funciones":
        extra.update(
            peliculas=Pelicula.objects.filter(activa=True).order_by("nombre"),
            salas=Sala.objects.all().order_by("nombre_sala"),
            precios=_precios_funcion(obj) if obj else PRECIOS_BASE,
            vendidas=obj.entradas.count() if obj else 0,
        )
    elif seccion == "productos":
        extra.update(
            categorias=CATEGORIAS,
            componentes=ProductoConfiteria.objects.filter(disponible=True).exclude(pk=pk),
            stock=25 if (obj and obj.disponible) else 0,
        )
    elif seccion == "usuarios":
        extra.update(tipos_cuenta=TIPOS_CUENTA)

    return render(request, f"cine_nido/panel/form_{seccion}.html", _panel(request, seccion, extra))


def panel_venta_detalle(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related("usuario").prefetch_related(
            "entradas__asiento",
            "entradas__funcion__pelicula",
            "entradas__funcion__sala",
            "detalles_confiteria__producto_confiteria",
        ),
        pk=pk,
    )
    if request.method == "POST":
        numero = compra.numero
        compra.delete()
        messages.warning(request, f"La venta {numero} fue anulada y los asientos quedaron disponibles.")
        return redirect("panel_listado", "ventas")
    return render(request, "cine_nido/panel/venta_detalle.html", _panel(request, "ventas", {"compra": compra}))


def _validar_codigo_entrada(codigo_raw):
    codigo = (codigo_raw or "").strip().upper()
    if not codigo:
        return {"valido": False, "clase": "error", "titulo": "Código vacío", "detalle": "Ingresa un código para validar."}

    # Formatos soportados: CN-000123-D5, CN-000123, 123, 123-D5
    m = re.match(r"^(?:CN-)?0*(\d+)(?:-([A-Z]+\d+))?$", codigo)
    if not m:
        return {
            "valido": False,
            "clase": "error",
            "titulo": "Entrada no válida",
            "detalle": f"El código '{codigo}' no tiene un formato válido.",
        }

    compra_id = int(m.group(1))
    asiento_cod = m.group(2)
    compra = Compra.objects.prefetch_related(
        "entradas__asiento",
        "entradas__funcion__pelicula",
        "entradas__funcion__sala",
        "detalles_confiteria__producto_confiteria",
    ).filter(pk=compra_id).first()

    if not compra:
        return {
            "valido": False,
            "clase": "error",
            "titulo": "Entrada no válida",
            "detalle": f"No existe la compra #{compra_id}.",
        }

    entradas = list(compra.entradas.all())
    if asiento_cod:
        entradas = [e for e in entradas if e.asiento.codigo.upper() == asiento_cod]
        if not entradas:
            return {
                "valido": False,
                "clase": "error",
                "titulo": "Entrada no válida",
                "detalle": f"El asiento {asiento_cod} no pertenece a la compra {compra.numero}.",
            }

    if entradas:
        primera = entradas[0]
        asientos_str = ", ".join(e.asiento.codigo for e in entradas)
        return {
            "valido": True,
            "clase": "",
            "compra_id": compra.id,
            "numero": compra.numero,
            "titulo": "Entrada válida",
            "detalle": f"{primera.funcion.pelicula.nombre} · {primera.funcion.sala.nombre_sala} · {primera.funcion.hora} · Asiento(s): {asientos_str}",
        }

    detalles_conf = list(compra.detalles_confiteria.all())
    if detalles_conf:
        resumen_conf = ", ".join(f"{d.cantidad}x {d.producto_confiteria.nombre}" for d in detalles_conf)
        return {
            "valido": True,
            "clase": "",
            "compra_id": compra.id,
            "numero": compra.numero,
            "titulo": "Retiro de confitería válido",
            "detalle": f"{compra.numero} · {resumen_conf}",
        }

    return {
        "valido": False,
        "clase": "error",
        "titulo": "Compra sin entradas",
        "detalle": f"La compra {compra.numero} no registra entradas activas.",
    }


def panel_validar(request):
    resultado_validacion = None
    codigo = ""
    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip()
        resultado_validacion = _validar_codigo_entrada(codigo)
    return render(request, "cine_nido/panel/validar.html", _panel(request, "validar", {
        "codigo": codigo,
        "resultado_validacion": resultado_validacion,
    }))


# ---------------------------- Serializadores y API REST (JSON) ----------------------------

def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _serializar_sala(sala, incluir_asientos=False):
    data = {
        "id": sala.id,
        "nombre_sala": sala.nombre_sala,
        "capacidad": sala.capacidad,
    }
    if incluir_asientos:
        data["asientos"] = [
            {"id": a.id, "fila": a.fila, "numero": a.numero, "codigo": a.codigo}
            for a in sala.asientos.order_by("fila", "numero")
        ]
    return data


def _serializar_pelicula(pelicula, incluir_funciones=False):
    data = {
        "id": pelicula.id,
        "nombre": pelicula.nombre,
        "portada": pelicula.portada,
        "sinopsis": pelicula.sinopsis,
        "fecha_estreno": pelicula.fecha_estreno.isoformat() if pelicula.fecha_estreno else None,
        "duracion": pelicula.duracion,
        "clasificacion": pelicula.clasificacion,
        "director": pelicula.director,
        "activa": pelicula.activa,
        "estado": pelicula.estado,
    }
    if incluir_funciones:
        data["funciones"] = [
            _serializar_funcion(f) for f in pelicula.funciones.select_related("sala").order_by("fecha_hora")
        ]
    return data


def _serializar_funcion(funcion):
    return {
        "id": funcion.id,
        "sala_id": funcion.sala_id,
        "sala": funcion.sala.nombre_sala,
        "pelicula_id": funcion.pelicula_id,
        "pelicula": funcion.pelicula.nombre,
        "fecha_hora": funcion.fecha_hora.isoformat(),
        "fecha": funcion.fecha.isoformat(),
        "hora": funcion.hora,
        "precio": funcion.precio,
    }


def _serializar_producto(producto):
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "foto": producto.foto,
        "precio_unitario": producto.precio_unitario,
        "disponible": producto.disponible,
        "categoria": producto.categoria,
    }


def _serializar_compra(compra):
    return {
        "id": compra.id,
        "numero": compra.numero,
        "usuario_id": compra.usuario_id,
        "usuario": compra.usuario.email or compra.usuario.username,
        "fecha_compra": compra.fecha_compra.isoformat(),
        "total": compra.total,
        "entradas": [
            {
                "id": e.id,
                "funcion_id": e.funcion_id,
                "pelicula": e.funcion.pelicula.nombre,
                "sala": e.funcion.sala.nombre_sala,
                "fecha_hora": e.funcion.fecha_hora.isoformat(),
                "asiento_id": e.asiento_id,
                "asiento": e.asiento.codigo,
                "precio": e.precio,
            }
            for e in compra.entradas.select_related("asiento", "funcion__pelicula", "funcion__sala")
        ],
        "detalles_confiteria": [
            {
                "id": d.id,
                "producto_id": d.producto_confiteria_id,
                "producto": d.producto_confiteria.nombre,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal": d.subtotal,
            }
            for d in compra.detalles_confiteria.select_related("producto_confiteria")
        ],
    }


@csrf_exempt
def api_salas(request):
    if request.method == "GET":
        salas = Sala.objects.all().order_by("id")
        return JsonResponse({"results": [_serializar_sala(s) for s in salas]})

    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        nombre_sala = (body.get("nombre_sala") or body.get("nombre") or "").strip()
        if not nombre_sala:
            return JsonResponse({"error": "El campo 'nombre_sala' es obligatorio."}, status=400)
        try:
            sala = Sala.objects.create(nombre_sala=nombre_sala)
            filas = int(body.get("filas") or 8)
            por_fila = int(body.get("por_fila") or 12)
            _asegurar_asientos_sala(sala, filas=filas, por_fila=por_fila)
            return JsonResponse(_serializar_sala(sala, incluir_asientos=True), status=201)
        except IntegrityError:
            return JsonResponse({"error": "Ya existe una sala con ese nombre."}, status=400)

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_sala_detalle(request, sala_id):
    sala = get_object_or_404(Sala, pk=sala_id)

    if request.method == "GET":
        _asegurar_asientos_sala(sala)
        return JsonResponse(_serializar_sala(sala, incluir_asientos=True))

    if request.method in ("PUT", "PATCH"):
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        nombre_sala = (body.get("nombre_sala") or body.get("nombre") or sala.nombre_sala).strip()
        if not nombre_sala:
            return JsonResponse({"error": "El nombre de la sala no puede estar vacío."}, status=400)
        try:
            sala.nombre_sala = nombre_sala
            sala.save()
            return JsonResponse(_serializar_sala(sala, incluir_asientos=True))
        except IntegrityError:
            return JsonResponse({"error": "Ya existe una sala con ese nombre."}, status=400)

    if request.method == "DELETE":
        try:
            sala.delete()
            return JsonResponse({"deleted": True})
        except ProtectedError:
            return JsonResponse(
                {"error": "No se puede eliminar la sala porque tiene funciones o entradas asociadas."},
                status=400,
            )

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_peliculas(request):
    if request.method == "GET":
        qs = Pelicula.objects.all().order_by("id")
        activa_param = request.GET.get("activa")
        if activa_param is not None:
            qs = qs.filter(activa=activa_param.lower() in ("true", "1", "si"))
        q = request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(director__icontains=q) | Q(sinopsis__icontains=q))
        estado = request.GET.get("estado")
        peliculas = [_serializar_pelicula(p) for p in qs]
        if estado:
            peliculas = [p for p in peliculas if p["estado"] == estado]
        return JsonResponse({"results": peliculas})

    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        nombre = (body.get("nombre") or "").strip()
        director = (body.get("director") or "").strip()
        clasificacion = (body.get("clasificacion") or "TE").strip()
        fecha_estreno = parse_date(str(body.get("fecha_estreno") or ""))
        try:
            duracion = int(body.get("duracion") or 0)
        except (ValueError, TypeError):
            duracion = 0

        if not nombre or not director or not fecha_estreno or duracion <= 0:
            return JsonResponse(
                {"error": "Campos obligatorios: nombre, director, fecha_estreno (YYYY-MM-DD) y duracion (>0)."},
                status=400,
            )

        pelicula = Pelicula.objects.create(
            nombre=nombre,
            portada=body.get("portada") or None,
            sinopsis=body.get("sinopsis") or "",
            fecha_estreno=fecha_estreno,
            duracion=duracion,
            clasificacion=clasificacion,
            director=director,
            activa=bool(body.get("activa", True)),
        )
        return JsonResponse(_serializar_pelicula(pelicula), status=201)

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_pelicula_detalle(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, pk=pelicula_id)

    if request.method == "GET":
        return JsonResponse(_serializar_pelicula(pelicula, incluir_funciones=True))

    if request.method in ("PUT", "PATCH"):
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        if "nombre" in body:
            pelicula.nombre = str(body["nombre"]).strip()
        if "portada" in body:
            pelicula.portada = body["portada"] or None
        if "sinopsis" in body:
            pelicula.sinopsis = str(body["sinopsis"])
        if "fecha_estreno" in body:
            fe = parse_date(str(body["fecha_estreno"]))
            if not fe:
                return JsonResponse({"error": "Formato de 'fecha_estreno' inválido (use YYYY-MM-DD)."}, status=400)
            pelicula.fecha_estreno = fe
        if "duracion" in body:
            pelicula.duracion = int(body["duracion"])
        if "clasificacion" in body:
            pelicula.clasificacion = str(body["clasificacion"]).strip()
        if "director" in body:
            pelicula.director = str(body["director"]).strip()
        if "activa" in body:
            pelicula.activa = bool(body["activa"])
        pelicula.save()
        return JsonResponse(_serializar_pelicula(pelicula, incluir_funciones=True))

    if request.method == "DELETE":
        try:
            pelicula.delete()
            return JsonResponse({"deleted": True})
        except ProtectedError:
            pelicula.activa = False
            pelicula.save(update_fields=["activa"])
            return JsonResponse({"deleted": False, "activa": False, "detail": "Película desactivada por tener funciones asociadas."})

    return JsonResponse({"error": "Método no permitido."}, status=405)


def _parsear_fecha_hora_api(body):
    if "fecha_hora" in body and body["fecha_hora"]:
        dt = parse_datetime(str(body["fecha_hora"]))
        if dt is None:
            raise ValidationError("Formato de 'fecha_hora' inválido (use ISO 8601).")
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    if "fecha" in body and "hora" in body:
        return _combinar_fecha_hora(body["fecha"], body["hora"])
    raise ValidationError("Debe proporcionar 'fecha_hora' o bien 'fecha' y 'hora'.")


@csrf_exempt
def api_funciones(request):
    if request.method == "GET":
        qs = Funcion.objects.select_related("pelicula", "sala").order_by("fecha_hora")
        if request.GET.get("pelicula_id"):
            qs = qs.filter(pelicula_id=request.GET["pelicula_id"])
        if request.GET.get("sala_id"):
            qs = qs.filter(sala_id=request.GET["sala_id"])
        if request.GET.get("fecha"):
            fecha = parse_date(request.GET["fecha"])
            if fecha:
                qs = [f for f in qs if f.fecha == fecha]
                return JsonResponse({"results": [_serializar_funcion(f) for f in qs]})
        return JsonResponse({"results": [_serializar_funcion(f) for f in qs]})

    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        try:
            sala = get_object_or_404(Sala, pk=body.get("sala_id") or body.get("sala"))
            pelicula = get_object_or_404(Pelicula, pk=body.get("pelicula_id") or body.get("pelicula"))
            fecha_hora = _parsear_fecha_hora_api(body)
            precio = int(body.get("precio", PRECIOS_BASE["general"]))
            funcion = Funcion.objects.create(
                sala=sala,
                pelicula=pelicula,
                fecha_hora=fecha_hora,
                precio=precio,
            )
            return JsonResponse(_serializar_funcion(funcion), status=201)
        except ValidationError as err:
            return JsonResponse({"error": err.messages[0]}, status=400)
        except IntegrityError:
            return JsonResponse({"error": "Ya existe una función en esa sala y horario."}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({"error": "Datos de función inválidos."}, status=400)

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_funcion_detalle(request, funcion_id):
    funcion = get_object_or_404(Funcion.objects.select_related("pelicula", "sala"), pk=funcion_id)

    if request.method == "GET":
        return JsonResponse(_serializar_funcion(funcion))

    if request.method in ("PUT", "PATCH"):
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        try:
            if "sala_id" in body or "sala" in body:
                funcion.sala = get_object_or_404(Sala, pk=body.get("sala_id") or body.get("sala"))
            if "pelicula_id" in body or "pelicula" in body:
                funcion.pelicula = get_object_or_404(Pelicula, pk=body.get("pelicula_id") or body.get("pelicula"))
            if "fecha_hora" in body or ("fecha" in body and "hora" in body):
                funcion.fecha_hora = _parsear_fecha_hora_api(body)
            if "precio" in body:
                funcion.precio = int(body["precio"])
            funcion.save()
            return JsonResponse(_serializar_funcion(funcion))
        except ValidationError as err:
            return JsonResponse({"error": err.messages[0]}, status=400)
        except IntegrityError:
            return JsonResponse({"error": "Ya existe una función en esa sala y horario."}, status=400)

    if request.method == "DELETE":
        try:
            funcion.delete()
            return JsonResponse({"deleted": True})
        except ProtectedError:
            return JsonResponse({"error": "No se puede eliminar una función con entradas vendidas."}, status=400)

    return JsonResponse({"error": "Método no permitido."}, status=405)


def api_funcion_asientos(request, funcion_id):
    if request.method != "GET":
        return JsonResponse({"error": "Método no permitido."}, status=405)
    funcion = get_object_or_404(Funcion.objects.select_related("pelicula", "sala"), pk=funcion_id)
    session_key = request.session.session_key
    mapa = _construir_mapa_sala(funcion, session_key=session_key)
    asientos_planos = [a for fila in mapa for a in fila["asientos"]]
    ocupados = sum(1 for a in asientos_planos if a["ocupado"])
    reservados = sum(1 for a in asientos_planos if a["reservado"])
    return JsonResponse({
        "funcion": _serializar_funcion(funcion),
        "total_asientos": len(asientos_planos),
        "ocupados": ocupados,
        "reservados": reservados,
        "disponibles": len(asientos_planos) - ocupados - reservados,
        "filas": mapa,
        "asientos": asientos_planos,
    })


@csrf_exempt
def api_reservar_asientos(request, funcion_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido."}, status=405)
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    asientos_input = body.get("asientos") or []
    if not asientos_input:
        return JsonResponse({"error": "Debe indicar al menos un asiento en 'asientos'."}, status=400)

    funcion = get_object_or_404(Funcion.objects.select_related("pelicula", "sala"), pk=funcion_id)
    session_key = body.get("session_key") or _asegurar_session_key(request)
    try:
        asientos_objs = _resolver_asientos_sala(funcion.sala, asientos_input)
        expira_ts = _reservar_asientos_temporalmente(funcion, asientos_objs, session_key)
    except ValidationError as err:
        return JsonResponse({"error": err.messages[0]}, status=400)

    return JsonResponse({
        "funcion_id": funcion.id,
        "asientos": [a.codigo for a in asientos_objs],
        "expira_en_segundos": TIEMPO_RESERVA_SEGUNDOS,
        "expira_ts": expira_ts,
    }, status=201)


@csrf_exempt
def api_confiteria(request):
    if request.method == "GET":
        qs = ProductoConfiteria.objects.all().order_by("id")
        disp = request.GET.get("disponible")
        if disp is not None:
            qs = qs.filter(disponible=disp.lower() in ("true", "1", "si"))
        return JsonResponse({"results": [_serializar_producto(p) for p in qs]})

    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        nombre = (body.get("nombre") or "").strip()
        try:
            precio_unitario = int(body.get("precio_unitario") if "precio_unitario" in body else body.get("precio", -1))
        except (ValueError, TypeError):
            precio_unitario = -1
        if not nombre or precio_unitario < 0:
            return JsonResponse({"error": "Campos obligatorios: nombre y precio_unitario (>= 0)."}, status=400)
        prod = ProductoConfiteria.objects.create(
            nombre=nombre,
            foto=body.get("foto") or None,
            precio_unitario=precio_unitario,
            disponible=bool(body.get("disponible", True)),
        )
        return JsonResponse(_serializar_producto(prod), status=201)

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_confiteria_detalle(request, producto_id):
    prod = get_object_or_404(ProductoConfiteria, pk=producto_id)

    if request.method == "GET":
        return JsonResponse(_serializar_producto(prod))

    if request.method in ("PUT", "PATCH"):
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)
        if "nombre" in body:
            prod.nombre = str(body["nombre"]).strip()
        if "foto" in body:
            prod.foto = body["foto"] or None
        if "precio_unitario" in body or "precio" in body:
            prod.precio_unitario = int(body.get("precio_unitario", body.get("precio")))
        if "disponible" in body:
            prod.disponible = bool(body["disponible"])
        prod.save()
        return JsonResponse(_serializar_producto(prod))

    if request.method == "DELETE":
        try:
            prod.delete()
            return JsonResponse({"deleted": True})
        except ProtectedError:
            prod.disponible = False
            prod.save(update_fields=["disponible"])
            return JsonResponse({"deleted": False, "disponible": False})

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_compras(request):
    if request.method == "GET":
        qs = Compra.objects.select_related("usuario").prefetch_related(
            "entradas__asiento",
            "entradas__funcion__pelicula",
            "entradas__funcion__sala",
            "detalles_confiteria__producto_confiteria",
        )
        if request.GET.get("usuario_id"):
            qs = qs.filter(usuario_id=request.GET["usuario_id"])
        elif request.user.is_authenticated and not request.user.is_staff:
            qs = qs.filter(usuario=request.user)
        return JsonResponse({"results": [_serializar_compra(c) for c in qs]})

    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "JSON inválido."}, status=400)

        usuario_modelo = get_user_model()
        if body.get("usuario_id"):
            usuario = get_object_or_404(usuario_modelo, pk=body["usuario_id"])
        else:
            usuario = _obtener_o_crear_usuario_compra(request, correo=body.get("correo", ""))

        funcion_id = body.get("funcion_id")
        asientos_input = body.get("asientos") or []
        confiteria_input = body.get("confiteria") or body.get("detalles_confiteria") or []

        if not asientos_input and not confiteria_input:
            return JsonResponse(
                {"error": "La compra debe incluir al menos 'asientos' (con 'funcion_id') o 'confiteria'."},
                status=400,
            )

        try:
            with transaction.atomic():
                compra = Compra.objects.create(usuario=usuario, total=0)
                total = 0

                if asientos_input:
                    if not funcion_id:
                        raise ValidationError("Debe indicar 'funcion_id' para comprar entradas.")
                    funcion = get_object_or_404(Funcion.objects.select_related("sala"), pk=funcion_id)
                    asientos_objs = _resolver_asientos_sala(funcion.sala, asientos_input)

                    if Entrada.objects.select_for_update().filter(
                        funcion=funcion, asiento__in=asientos_objs
                    ).exists():
                        raise ValidationError("Uno o más asientos ya están ocupados para esta función.")

                    precio_entrada = int(body.get("precio_entrada") or funcion.precio)
                    for asiento in asientos_objs:
                        entrada_obj = Entrada(
                            compra=compra,
                            funcion=funcion,
                            asiento=asiento,
                            precio=precio_entrada,
                        )
                        entrada_obj.full_clean()
                        entrada_obj.save()
                        total += precio_entrada

                for item in confiteria_input:
                    prod_id = item.get("producto_id") or item.get("producto_confiteria_id") or item.get("id")
                    cantidad = int(item.get("cantidad", 1))
                    if cantidad <= 0:
                        continue
                    prod = get_object_or_404(ProductoConfiteria, pk=prod_id)
                    if not prod.disponible:
                        raise ValidationError(f"El producto '{prod.nombre}' no está disponible.")
                    precio_unit = int(item.get("precio_unitario") or prod.precio_unitario)
                    DetalleConfiteria.objects.create(
                        compra=compra,
                        producto_confiteria=prod,
                        cantidad=cantidad,
                        precio_unitario=precio_unit,
                    )
                    total += cantidad * precio_unit

                compra.total = total
                compra.save(update_fields=["total"])
                return JsonResponse(_serializar_compra(compra), status=201)
        except ValidationError as err:
            msg = err.messages[0] if hasattr(err, "messages") and err.messages else str(err)
            return JsonResponse({"error": msg}, status=400)
        except IntegrityError:
            return JsonResponse({"error": "Asiento duplicado u ocupado para esta función."}, status=400)

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_compra_detalle(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("usuario").prefetch_related(
            "entradas__asiento",
            "entradas__funcion__pelicula",
            "entradas__funcion__sala",
            "detalles_confiteria__producto_confiteria",
        ),
        pk=compra_id,
    )

    if request.method == "GET":
        return JsonResponse(_serializar_compra(compra))

    if request.method == "DELETE":
        compra.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"error": "Método no permitido."}, status=405)


@csrf_exempt
def api_validar_entrada(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido."}, status=405)
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    codigo = body.get("codigo") or (f"CN-{int(body['compra_id']):06d}" if body.get("compra_id") else "")
    resultado = _validar_codigo_entrada(codigo)
    status_code = 200 if resultado.get("valido") else 404
    return JsonResponse(resultado, status=status_code)
