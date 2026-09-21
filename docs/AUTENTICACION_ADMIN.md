# Autenticación y autorización administrativa

## Inspección previa al cambio — 21 de septiembre de 2026

Antes de esta tarea Mensuales no tenía JWT/SSO, /auth/sso ni los demás endpoints
de sesión. No esperaba issuer, audience, sub, usuario, email ni otros claims de
un JWT; tampoco creaba sesión interna, cookie o timeout de inactividad.
Existían IdentityService, el proveedor callable de correo y los permisos
administrativos de frontend/backend. El repositorio estaba limpio en e566ab0.
No se encontró un dominio mensual previsto en código ni documentación.

En Apps Script, `Session.getActiveUser().getEmail()` identificaba al usuario activo
de la aplicación. Su correo se normalizaba con trim y minúsculas y se contrastaba
con `CORREOS_ADMIN`. La dirección original autorizada era:

`info.costos@crepesywafflesantioquia.com`

## Contrato implementado en Python

`IdentityService` conserva su proveedor sin argumentos. Con `AUTH_ENABLED=true`,
`register_auth` lo conecta al `sub` de `g.auth_session`, después de validar la
cookie interna. Un proveedor externo inyectado no puede reemplazar esa identidad
cuando está habilitado el SSO.
`sub` contiene el `user_login` de WordPress, que es la identidad autorizada. El servicio
aplica `strip().lower()` y compara con `ADMIN_USER_LOGINS`, leído del entorno al crear
la aplicación. La lista se separa por comas, ignora entradas vacías y duplicadas, y
rechaza comodines y caracteres de control. Si falta o está vacía, nadie es administrador.
No hay administradores fijos en el backend. Para agregar o retirar permisos se modifica
esa variable y se aplica la nueva configuración al proceso/contenedor, sin cambiar código.
El proveedor se consulta nuevamente en cada operación; no se cachea la autorización.

La autenticación WordPress/JWT ya está implementada: RS256 de corta vida,
validación de firma/emisor/audience/claims y canje por sesión interna HS256.
El nombre de usuario solo procede del JWT firmado por WordPress. No se obtiene de querystring,
JSON sin firma, campos de formulario adicionales, Base64, localStorage ni headers.
La clave privada de WordPress nunca se necesita en Flask.

`credentials/credentials.json` y `credentials/token.json` permiten al proceso
Python consultar Drive y Sheets como cuenta técnica. **Ese OAuth no identifica
al usuario del navegador ni concede administración**, aunque la cuenta técnica
coincida con un identificador configurado como administrador.

## Comportamiento comprobado

| Identidad entregada por el proveedor verificado | Administración |
|---|---|
| `user_login` incluido en ADMIN_USER_LOGINS | Permitida |
| `user_login` no incluido | Denegada solo para funciones administrativas |
| Mismo login en mayúsculas o con espacios externos | Permitida tras normalizar |
| `email` coincide, pero `sub` no está incluido | Denegada |
| ADMIN_USER_LOGINS vacío o ausente | Denegada para todos |
| Usuario no autenticado | Denegada |

La configuración local conserva `AUTH_ENABLED=false`: sin proveedor inyectado,
el botón permanece oculto y los endpoints administrativos responden 403. Con SSO
habilitado y sin sesión válida se responde 401, incluso antes de comprobar permisos.
Un `sub` faltante, vacío o inválido se rechaza en el login; `email` no se exige ni se usa.
No existe un usuario falso
de producción; `APP_ENV=production` exige autenticación, cookie Secure y DEBUG=false.
Las identidades simuladas se definen exclusivamente en `tests/` y sus aplicaciones
usan `TESTING=True`. Esa opción por sí sola tampoco concede permisos.

El botón Administración comienza oculto. `obtenerEstadoAdministrador` lo muestra
solamente si devuelve `esAdministrador=true`; false o error lo mantienen oculto.
El backend vuelve a autorizar consolidado, CSV y plano Siesa mediante
`IdentityService.require_admin` antes de consultar datos. Ocultar o modificar
el botón no cambia los permisos.

El usuario normal autenticado puede cargar PDV, categorías y productos, Guardar
borrador, Finalizar y usar actividad/estado de sesión. Consultar
`obtenerEstadoAdministrador` devuelve HTTP 200 con `esAdministrador=false`;
los endpoints exclusivamente administrativos siguen devolviendo HTTP 403.

Evidencia: `tests/test_identity.py` comprueba la lista configurable de usuarios, autorización
de cada endpoint, reevaluación por solicitud, independencia del OAuth y rechazo
de identidad falsificada mediante querystring, JSON, Base64 y encabezados.
`tests/test_frontend.py` comprueba interfaz administrativa, usuario normal,
ausencia de identidad y fallo al consultar el estado.

## JWT de WordPress

Endpoint exacto: `POST /auth/sso`, formulario con un único campo `token`.
No acepta token en URL ni JSON. Responde 303 hacia / y establece la cookie interna.
El token SSO no se devuelve en la URL, página, logs ni cookie de sesión.

| Claim | Política Mensuales |
|---|---|
| alg / typ | RS256 / JWT; rechaza none, HS256 y extensiones crit |
| iss | `calco-intranet` |
| aud | `inventarios-mensuales`; valor NUEVO definido en esta tarea |
| sub | Obligatorio; user_login no vacío, hasta 256 caracteres |
| usuario | Opcional; si viene debe coincidir exactamente con sub |
| email | No requerido; se ignora si está presente, sin conceder permisos |
| iat / nbf / exp | Enteros; iat ≤ nbf < exp; vida máxima predeterminada 60 segundos |
| jti | Obligatorio, texto no vacío hasta 256 caracteres; consumo único |

El margen de reloj SSO es 10 segundos como en Uno a Uno; la sesión interna no
tiene ese margen. Un token para `inventarios-uno-a-uno` se rechaza en Mensuales,
incluso firmado con la misma clave RSA. El snippet firma sub y usuario con
`$user->user_login`. El snippet de referencia ya no incluye email para Mensuales;
conserva ese campo para Uno a Uno para no modificar su contrato.

## Sesión e inactividad: misma política de Uno a Uno

`SESSION_IDLE_TIMEOUT_SECONDS=1200` significa **20 minutos desde la última actividad
real**, no desde el login. La sesión puede continuar mientras haya actividad.
La cookie se llama `inventario_mensual_session` y contiene un JWT HS256 propio:
iss `inventarios-mensuales`, aud `inventarios-mensuales-session`, sub, iat,
act, exp y sid. El secreto de esta sesión debe ser independiente del de Uno a Uno,
de RSA y de OAuth. Cookie HttpOnly, SameSite=Lax, Path=/ y sin Domain compartido;
Secure es obligatorio en producción. Su Max-Age es el tiempo de sesión restante.

Las sesiones anteriores con `email` adicional siguen validando su firma, expiración
y `sub`; ese email se ignora para autorizar. Si se retira el login de la configuración,
la instancia que cargue la nueva lista lo deniega incluso con una cookie aún vigente.

Se reutilizaron SessionAuthService y auth.js del repositorio local de Uno a Uno:

- Eventos confiables click, keydown, input, scroll, touchstart y mousemove registran
  actividad; eventos sintéticos no renuevan.
- POST /auth/activity comunica idle_seconds, con máximo un envío cada 45 segundos.
  Un envío retrasado conserva el momento del evento, no lo reemplaza por la recepción.
- La comprobación cada 5 segundos no genera actividad. /auth/status, /healthz,
  navegación y consultas API tampoco extienden la sesión.
- A los 1200 segundos sin actividad confirmada, el backend rechaza con 401.
  Una cookie expirada no se puede renovar.
- Pestañas comparten metadatos de actividad y consultan la cookie vigente. Una
  pestaña vencida no hace logout automático ni borra la cookie renovada por otra.
- Ante expiración se muestra /auth/expired. El borrador mensual no se elimina;
  al regresar desde la intranet se recupera al elegir el mismo PDV, fecha y categoría.
- El logout explícito elimina la cookie. Como en Uno a Uno, no hay lista central de
  revocación de JWT internos; una copia previa conserva su vencimiento firmado.

auth.js conserva el algoritmo de Uno a Uno; solo cambian la clave de metadatos
`inventario-mensual-auth-v1-...` y el header existente de Mensuales
`X-Monthly-Request: 1`. Los JWT nunca se guardan en localStorage.
monthly.js y las reglas de Guardar/Finalizar no se modificaron.

Referencia exacta inspeccionada de Uno a Uno (SHA-256):

- session_auth_service.py: `1bc4b98cb8777330a59aad8adb800335382b64bd48c10aaaf6e4220bf4b70a0a`.
- auth.js: `8222af253b2900eef5712d172f3c4ef370f5ce1b26a12ff4c10a2a5c86633953`.

## Endpoints y permisos

| Endpoint | Acceso con AUTH_ENABLED=true |
|---|---|
| POST /auth/sso | Público; exige JWT RS256 válido |
| POST /auth/activity | Sesión vigente + header/origen válidos; renueva por actividad |
| GET o POST /auth/status | Sesión vigente; consulta sin renovación |
| POST /auth/logout | Sesión vigente + header/origen válidos; elimina cookie |
| GET /auth/expired | Público; pantalla de reingreso |
| GET /healthz | Público; devuelve status=ok sin Google |
| /, /api/* y archivos estáticos | Sesión vigente |
| Consolidado, CSV y Siesa | Además, user_login incluido en ADMIN_USER_LOGINS |

POST /auth/status conserva la convención real de Uno a Uno. GET es la misma
operación consultiva solicitada, sin un segundo mecanismo de estado.
Las mutaciones requieren X-Monthly-Request: 1 y rechazan Origin de otro esquema/host
o Sec-Fetch-Site: cross-site. No se confía en headers de identidad.

## Proxy HTTPS y diagnóstico de origen

La fábrica ya configura `ProxyFix(x_for=0, x_proto=1, x_host=0, x_port=1, x_prefix=0)`.
Confía en un salto de Apache para protocolo/puerto y mantiene el Host preservado
por Apache. El backend debe seguir limitado a `127.0.0.1:8089`.
Con `Host: inventarios-mensuales.calcoweb.net`, `X-Forwarded-Proto: https` y
`X-Forwarded-Port: 443`, Flask obtiene esquema `https`, host sin puerto por defecto
y `host_url=https://inventarios-mensuales.calcoweb.net/`. TRUSTED_HOSTS sigue activo.

Tanto api.js como auth.js envían `X-Monthly-Request: 1` y
`credentials: same-origin`. No requieren cambios. Las pruebas simulan POST SSO y
redirección desde una intranet de otro sitio y desde un subdominio del mismo sitio:
los fetch posteriores envían Origin de Mensuales. Chromium corre sin red y todas
las solicitudes se interceptan hacia Flask test client. Fetch Metadata puede no
estar aún disponible en esa fase de interceptación; los casos HTTP verifican
explícitamente same-origin, same-site y cross-site. Same-site no permite un Origin
distinto; cross-site sigue rechazado. No se amplió la política de origen.

El operador confirmó que ProxyFix también estaba instalado con esos parámetros
en el contenedor. El VirtualHost HTTPS activo, identificado por `apache2ctl -S`
en `/etc/apache2/sites-enabled/inventarios-mensuales-le-ssl.conf`, enviaba realmente
`X-Forwarded-Proto: http` y `X-Forwarded-Port: 80`. Las pruebas reproducen con esos
valores el 403 en actividad, PDV y estado administrativo: Flask reconstruye HTTP
y falla la comparación del esquema con el Origin HTTPS, aunque host, marcador
y Sec-Fetch-Site sean correctos. La cookie de sesión se valida antes.

La corrección externa pendiente es usar en ese VirtualHost de puerto 443:

```apache
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-Port "443"
```

Se conservan ProxyPreserveHost y el destino `http://127.0.0.1:8089/` del proxy.
Con las dos cabeceras corregidas, las mismas solicitudes de prueba devuelven
204 en actividad y 200 en PDV/estado administrativo. No hacen falta cambios en
.env, frontend ni en la comparación de Origin. Esta tarea no modifica Apache,
no aplica la corrección en producción ni conserva logging temporal de diagnóstico.

## Replay y alcance

ReplayCache consume jti atómicamente bajo lock en RAM, con TTL que cubre exp más
margen y al menos 90 segundos. Reutilizarlo entre clientes/hilos se rechaza.
Es el mismo alcance de Uno a Uno: un proceso compartido por sus hilos.
No coordina distintos procesos/réplicas ni conserva consumos después de reiniciar.
No se añadió infraestructura ni se modificó el despliegue; el responsable debe
respetar ese alcance cuando configure la ejecución.

## Configuración pendiente del operador

.env.example contiene los valores y no contiene claves. Localmente continúa
AUTH_ENABLED=false y GOOGLE_WRITES_ENABLED=false. Para el entorno autenticado
debe suministrarse la clave pública RSA PEM mediante SSO_PUBLIC_KEY_PATH y un
SESSION_JWT_SECRET propio de al menos 32 bytes aleatorios. Se rechazan claves
privadas, claves no RSA, RSA menor a 2048 bits y secretos insuficientes.

El operador configurará APP_ENV=production, AUTH_ENABLED=true, SESSION_COOKIE_SECURE=true,
el enlace INTRANET_URL y
`TRUSTED_HOSTS=localhost,127.0.0.1,inventarios-mensuales.calcoweb.net`.
SESSION_IDLE_TIMEOUT_SECONDS permanece en 1200. Configurar también `ADMIN_USER_LOGINS`
con los nombres de usuario exactos de WordPress, separados por comas. Ejemplo de formato
(sustituir los valores de ejemplo por usuarios reales):

```env
ADMIN_USER_LOGINS=usuario.uno,usuario.dos@example.test
```

Un identificador con formato de correo solo corresponde si es realmente `user_login`;
no se consulta `user_email` ni se deduce el usuario quitando el dominio. Los siete valores
confirmados por el operador se guardaron en el `.env` local, excluido de Git; deben
configurarse también en el entorno de producción al aplicar este cambio.
El snippet anterior ya firma `sub=user_login` y sigue siendo compatible; actualizar
la referencia Woody elimina el email del token mensual, pero no es requisito para
que el backend use el login. Este cambio no requiere modificar Apache.
No se crearon claves de producción ni se cambiaron paths, WordPress o infraestructura.

## Snippet Woody para los dos aplicativos

Propuesta: [WOODY_INVENTARIOS_UNIFICADO.php](WOODY_INVENTARIOS_UNIFICADO.php).
Es el reemplazo del mismo snippet, no un segundo sistema. No se ejecutó localmente
ni se publicó en WordPress. Se conservan nonce, login WordPress, formulario POST
con token, firma RS256 de 60 segundos, destino y audience actuales de Uno a Uno.
Un formulario antiguo sin selector sigue dirigiéndose a Uno a Uno.

El selector calco_inventarios_app solo admite uno_a_uno o mensual. Audiences y
destinos provienen de una whitelist fija del servidor; no se acepta una URL del
navegador. Ambos tokens incluyen `sub` y `usuario` con `user_login`. Solo el token de
Uno a Uno conserva el campo email; Mensuales no depende de él.

Reemplazar **`__INVENTARIOS_MENSUALES_URL__`** por la URL HTTPS base real de Mensuales,
**sin barra final ni /auth/sso**. El snippet ya añade /auth/sso. Mientras quede el
placeholder, solo el acceso Mensuales responde “aún no está configurado”; Uno a Uno
conserva su destino funcional. Si Woody proporciona la etiqueta PHP, omitir la línea
inicial `<?php` al pegar. No modificar el audience Uno a Uno ni su URL.

Se recomienda reutilizar la RSA existente para este mismo emisor de confianza:
WordPress mantiene `/etc/calco-intranet/inventarios-uno-a-uno/private.pem` y ambos
backends reciben solamente la pública. La separación depende de validar cada
audience; esta validación es obligatoria cuando un emisor atiende varias aplicaciones.
Una clave separada permitiría rotación y aislamiento por aplicativo, a costa de
gestionar otra pareja; no resulta necesaria para el patrón solicitado.
Referencia: [RFC 8725, sección 3.9](https://www.rfc-editor.org/rfc/rfc8725.html#section-3.9).

Validación de algoritmos/claims basada en la [API oficial de PyJWT](https://pyjwt.readthedocs.io/en/stable/api.html);
atributos de cookie según las [consideraciones de seguridad de Flask](https://flask.palletsprojects.com/en/stable/web-security/).
No se infiere identidad administrativa del contenido de OAuth.

## Evidencia de pruebas

tests/test_sso.py usa RSA efímera en memoria y reloj controlado. Cubre firma,
algoritmo, audiencia, issuer, claims obligatorios, user_login, email ignorado, replay concurrente,
cookie, sesión deslizante, estado sin renovación, logout, configuración y permisos.
tests/auth_frontend.cjs ejecuta el auth.js real con reloj y dos pestañas simuladas,
con y sin localStorage, hasta 40 minutos de actividad y expiración posterior.
tests/test_sso_browser.py transporta la cookie real emitida por el endpoint de
prueba a Chromium y comprueba expiración por timer/401, borrador intacto y recuperación
tras otro login. El 303 del canje se verifica por separado con Flask test client.
Ninguna de estas pruebas usa WordPress/Google reales ni abre un servidor.

Registro anterior de producción y administrador temporal: 193 pruebas específicas aprobadas
(test_sso, test_identity, test_sso_browser y test_config), seguidas de 351 pruebas
aprobadas en la suite completa con `python -B -m pytest -q`, sin fallos ni omisiones.
Incluye seis recorridos de navegador con SSO simulado y Guardar/Finalizar contra
fakes, y la reproducción del 403 con las directivas Apache reales aportadas.

Revisión posterior de user_login y ADMIN_USER_LOGINS: **217 pruebas específicas y
375 en la suite completa aprobadas**, sin fallos ni omisiones. Verifica que email
no concede permisos, que la configuración admite logins con formato de correo,
que no existen administradores implícitos y que la lista nueva se aplica incluso
a sesiones previamente emitidas. No cambió la lógica de inventario ni se usó Google real.
