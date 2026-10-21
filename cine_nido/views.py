import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST


User = get_user_model()
EMAIL_VALIDATOR = EmailValidator()


def _read_json(request):
    if request.content_type != "application/json":
        return None, JsonResponse(
            {"error": "El encabezado Content-Type debe ser application/json."}, status=415
        )

    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "El cuerpo debe contener JSON válido."}, status=400)

    if not isinstance(data, dict):
        return None, JsonResponse({"error": "El cuerpo JSON debe ser un objeto."}, status=400)
    return data, None


def _user_json(user):
    return {
        "id": user.pk,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": user.date_joined.isoformat(),
    }


def _email_value(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Ingresa un correo electrónico.")
    email = value.strip().lower()
    EMAIL_VALIDATOR(email)
    return email


def _name_value(field, value):
    if not isinstance(value, str):
        raise ValidationError("Este campo debe ser texto.")
    value = value.strip()
    max_length = User._meta.get_field(field).max_length
    if len(value) > max_length:
        raise ValidationError(f"Este campo admite hasta {max_length} caracteres.")
    return value


def _password_errors(password, user=None):
    if not isinstance(password, str) or not password:
        return ["La contraseña es obligatoria."]
    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return error.messages
    return []


def _validation_response(error, field=None):
    message = error.messages if isinstance(error, ValidationError) else [str(error)]
    body = {"error": "Revisa los datos enviados.", "details": message}
    if field:
        body["field"] = field
    return JsonResponse(body, status=400)


def _require_authenticated(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Debes iniciar sesión."}, status=401)
    return None


@ensure_csrf_cookie
@require_GET
def csrf_token(request):
    """Set the CSRF cookie and return the token needed by browser clients."""
    return JsonResponse({"csrf_token": get_token(request)})


@require_POST
def register(request):
    data, error_response = _read_json(request)
    if error_response:
        return error_response

    allowed_fields = {"email", "password", "password_confirmation", "first_name", "last_name"}
    unknown_fields = sorted(set(data) - allowed_fields)
    if unknown_fields:
        return JsonResponse(
            {"error": "Hay campos que no se pueden registrar.", "fields": unknown_fields},
            status=400,
        )

    try:
        email = _email_value(data.get("email"))
    except ValidationError as error:
        return _validation_response(error, "email")

    password = data.get("password")
    if password != data.get("password_confirmation"):
        return JsonResponse(
            {"error": "Las contraseñas no coinciden.", "field": "password_confirmation"},
            status=400,
        )
    password_errors = _password_errors(password)
    if password_errors:
        return JsonResponse(
            {"error": "La contraseña no cumple los requisitos.", "details": password_errors},
            status=400,
        )

    try:
        first_name = _name_value("first_name", data.get("first_name", ""))
        last_name = _name_value("last_name", data.get("last_name", ""))
    except ValidationError as error:
        return _validation_response(error)

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"error": "Ya existe una cuenta con ese correo."}, status=409)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
    except IntegrityError:
        return JsonResponse({"error": "Ya existe una cuenta con ese correo."}, status=409)

    return JsonResponse({"user": _user_json(user)}, status=201)


@require_POST
def sign_in(request):
    data, error_response = _read_json(request)
    if error_response:
        return error_response

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return JsonResponse(
            {"error": "El correo y la contraseña son obligatorios."}, status=400
        )

    user = authenticate(request, email=email.strip().lower(), password=password)
    if user is None:
        return JsonResponse({"error": "Correo o contraseña incorrectos."}, status=401)

    login(request, user)
    return JsonResponse({"user": _user_json(user)})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({"message": "Sesión cerrada."})


@require_http_methods(["GET", "PATCH"])
def current_user(request):
    authentication_error = _require_authenticated(request)
    if authentication_error:
        return authentication_error

    if request.method == "GET":
        return JsonResponse({"user": _user_json(request.user)})

    data, error_response = _read_json(request)
    if error_response:
        return error_response

    if not data:
        return JsonResponse({"error": "Envía al menos un campo para modificar."}, status=400)

    editable_fields = {"email", "first_name", "last_name"}
    unknown_fields = sorted(set(data) - editable_fields)
    if unknown_fields:
        return JsonResponse(
            {"error": "Hay campos que no se pueden modificar aquí.", "fields": unknown_fields},
            status=400,
        )

    user = request.user
    if "email" in data:
        try:
            email = _email_value(data["email"])
        except ValidationError as error:
            return _validation_response(error, "email")
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return JsonResponse({"error": "Ya existe una cuenta con ese correo."}, status=409)
        user.email = email

    try:
        for field in ("first_name", "last_name"):
            if field in data:
                setattr(user, field, _name_value(field, data[field]))
    except ValidationError as error:
        return _validation_response(error)

    try:
        changed_fields = [field for field in ("email", "first_name", "last_name") if field in data]
        user.save(update_fields=changed_fields)
    except IntegrityError:
        return JsonResponse({"error": "Ya existe una cuenta con ese correo."}, status=409)

    return JsonResponse({"user": _user_json(user)})


@require_POST
def change_password(request):
    authentication_error = _require_authenticated(request)
    if authentication_error:
        return authentication_error

    data, error_response = _read_json(request)
    if error_response:
        return error_response

    allowed_fields = {"current_password", "new_password", "password_confirmation"}
    unknown_fields = sorted(set(data) - allowed_fields)
    if unknown_fields:
        return JsonResponse(
            {"error": "Hay campos que no se pueden cambiar aquí.", "fields": unknown_fields},
            status=400,
        )

    current_password = data.get("current_password")
    if not isinstance(current_password, str) or not request.user.check_password(current_password):
        return JsonResponse({"error": "La contraseña actual es incorrecta."}, status=400)

    new_password = data.get("new_password")
    if new_password != data.get("password_confirmation"):
        return JsonResponse(
            {"error": "Las contraseñas no coinciden.", "field": "password_confirmation"},
            status=400,
        )
    password_errors = _password_errors(new_password, user=request.user)
    if password_errors:
        return JsonResponse(
            {"error": "La contraseña no cumple los requisitos.", "details": password_errors},
            status=400,
        )

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    login(request, request.user)
    return JsonResponse({"message": "Contraseña actualizada."})
