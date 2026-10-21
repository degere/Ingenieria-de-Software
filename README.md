# Sistema de Venta de Entradas de Cine Nido

Backend Django para registro de usuarios, inicio de sesión por correo y administración del perfil.

## Preparar el entorno

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

La configuración local usa SQLite. Para entrar al panel `/admin/`, crea un administrador con `python manage.py createsuperuser`.

## API de usuarios

Las solicitudes que envían datos deben usar `Content-Type: application/json`. La autenticación utiliza sesiones de Django; antes de cada flujo que use `POST` o `PATCH`, consulta `GET /api/auth/csrf/`, conserva la cookie y envía su token en el encabezado `X-CSRFToken`.

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| `GET` | `/` | Público | Muestra el estado del backend y el índice de rutas. |
| `GET` | `/api/auth/csrf/` | Público | Obtiene un token CSRF y configura su cookie. |
| `POST` | `/api/auth/register/` | Público | Registra una cuenta. Recibe `email`, `password`, `password_confirmation` y opcionalmente `first_name`, `last_name`. |
| `POST` | `/api/auth/login/` | Público | Inicia sesión. Recibe `email` y `password`. |
| `POST` | `/api/auth/logout/` | Público | Cierra la sesión actual. |
| `GET` | `/api/users/me/` | Sesión iniciada | Devuelve el perfil actual. |
| `PATCH` | `/api/users/me/` | Sesión iniciada | Modifica `email`, `first_name` y/o `last_name`. |
| `POST` | `/api/users/me/password/` | Sesión iniciada | Cambia la contraseña con `current_password`, `new_password` y `password_confirmation`. |

El correo se valida y debe ser único. Django almacena las contraseñas mediante su sistema de hash y aplica los validadores configurados en `settings.py`.
