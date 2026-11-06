
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from . import datos_demo as demo


# ---------------------------- Público ----------------------------

def cartelera(request):
    q = request.GET.get("q", "").strip()
    peliculas = demo.PELICULAS
    if q:
        peliculas = [p for p in peliculas if q.lower() in p["nombre"].lower() or q.lower() in p["genero"].lower()]
    return render(request, "cine_nido/cartelera.html", {
        "q": q,
        "en_cartelera": [p for p in peliculas if p["estado"] == "en_cartelera"],
        "proximos": [p for p in peliculas if p["estado"] == "proximo"],
    })


def pelicula_detalle(request, pelicula_id):
    pelicula = demo.obtener_pelicula(pelicula_id)
    if not pelicula:
        raise Http404("Película no encontrada")
    return render(request, "cine_nido/pelicula_detalle.html", {
        "pelicula": pelicula,
        "dias": demo.funciones_por_dia(pelicula_id),
    })


# ---------------------------- Compra (5 pasos) ----------------------------

def asientos(request, funcion_id):
    funcion = demo.obtener_funcion(funcion_id)
    if not funcion:
        raise Http404("Función no encontrada")
    return render(request, "cine_nido/asientos.html", {
        "funcion": funcion,
        "pelicula": demo.obtener_pelicula(funcion["pelicula_id"]),
        "mapa": demo.mapa_sala(funcion_id),
        "precios": demo.PRECIOS,
    })


def confiteria(request):
    # DEMO: valores fijos que luego saldrán de la compra en curso
    return render(request, "cine_nido/confiteria.html", {
        "categorias": demo.productos_por_categoria(),
        "resumen": {"pelicula": "Noche en el Muelle", "asientos": "D5, D6", "base": 11000},
    })


def pago(request):
    return render(request, "cine_nido/pago.html", {
        "resumen": {"pelicula": "Noche en el Muelle", "funcion": "Sala 1 · 20:30", "asientos": "D5, D6",
                    "entradas": 11000, "confiteria": 9900, "total": 20900},
    })


def entrada(request, compra_id):
    compra = next((c for c in demo.COMPRAS if c["id"] == compra_id), None)
    if not compra:
        raise Http404("Compra no encontrada")
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
    return render(request, "cine_nido/recuperar.html")


def mis_compras(request):
    return render(request, "cine_nido/mis_compras.html", {"compras": demo.COMPRAS})


# ---------------------------- Panel interno ----------------------------

def _panel(seccion_activa, extra=None):
    ctx = {"seccion_activa": seccion_activa, "secciones": demo.PANEL_SECCIONES}
    ctx.update(extra or {})
    return ctx


def panel_dashboard(request):
    return render(request, "cine_nido/panel/dashboard.html", _panel("dashboard", {
        "proximas": [dict(f, pelicula=demo.obtener_pelicula(f["pelicula_id"])["nombre"]) for f in demo.FUNCIONES[:5]],
    }))


def panel_listado(request, seccion):
    datos = demo.PANEL_SECCIONES.get(seccion)
    if not datos:
        raise Http404("Sección no encontrada")
    return render(request, "cine_nido/panel/listado.html", _panel(seccion, {
        "datos": datos,
        "tiene_formulario": seccion in demo.SECCIONES_CON_FORMULARIO,
    }))


def panel_formulario(request, seccion, pk=None):
    datos = demo.PANEL_SECCIONES.get(seccion)
    if not datos or seccion not in demo.SECCIONES_CON_FORMULARIO:
        raise Http404("Sección sin formulario")
    obj = demo.obtener_registro(seccion, pk) if pk else None
    if pk and obj is None:
        raise Http404("Registro no encontrado")

    if request.method == "POST":
        if request.POST.get("accion") == "baja":
            messages.warning(request, "Demo: el registro se daría de baja (todavía no se guarda nada).")
        else:
            messages.success(request, "Demo: los datos se guardarían correctamente (todavía no se guarda nada).")
        return redirect("panel_listado", seccion)

    extra = {"datos": datos, "obj": obj, "editando": pk is not None, "pk": pk}
    if seccion == "peliculas":
        extra.update(generos=demo.GENEROS, clasificaciones=demo.CLASIFICACIONES, idiomas=demo.IDIOMAS,
                     formatos=demo.FORMATOS, estados=demo.ESTADOS_PELICULA)
    elif seccion == "funciones":
        extra.update(peliculas=[p for p in demo.PELICULAS if p["estado"] != "fuera"], salas=demo.SALAS,
                     precios=demo.PRECIOS, vendidas=(pk * 7) % 96 if pk else 0)
    elif seccion == "productos":
        extra.update(categorias=demo.CATEGORIAS, componentes=[p for p in demo.PRODUCTOS if p["categoria"] != "Combos"],
                     stock=8 + obj["id"] * 5 if obj else None)
    elif seccion == "usuarios":
        extra.update(tipos_cuenta=demo.TIPOS_CUENTA)
    return render(request, "cine_nido/panel/form_%s.html" % seccion, _panel(seccion, extra))


def panel_venta_detalle(request, pk):
    compra = demo.obtener_compra(pk)
    if not compra:
        raise Http404("Venta no encontrada")
    if request.method == "POST":
        messages.warning(request, "Demo: la venta se anularía y los asientos quedarían libres (todavía no se guarda nada).")
        return redirect("panel_listado", "ventas")
    return render(request, "cine_nido/panel/venta_detalle.html", _panel("ventas", {"compra": compra}))


def panel_validar(request):
    return render(request, "cine_nido/panel/validar.html", _panel("validar"))
