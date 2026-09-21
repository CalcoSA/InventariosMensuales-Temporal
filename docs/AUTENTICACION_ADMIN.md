# Autenticación y autorización administrativa

En Apps Script, `Session.getActiveUser().getEmail()` identificaba al usuario activo
de la aplicación. Su correo se normalizaba con trim y minúsculas y se contrastaba
con `CORREOS_ADMIN`. La única dirección autorizada sigue siendo:

`info.costos@crepesywafflesantioquia.com`

## Contrato implementado en Python

`IdentityService` reutiliza un proveedor sin argumentos que devuelve el correo
corporativo autenticado de la solicitud actual, o `None` cuando no hay identidad.
Se conecta mediante `create_app(identity_provider=proveedor_verificado)`.
El servicio aplica `strip().lower()` y compara con la dirección exacta anterior.
El proveedor se consulta nuevamente en cada operación; no se cachea la autorización.

La integración de producción debe autenticar la sesión o validar el token SSO
(firma, emisor, destinatario y vigencia), obtener de ese resultado el correo
corporativo verificado y entregarlo al proveedor. El proveedor no puede tomar
el correo directamente del navegador, querystring, JSON, Base64 ni encabezados
públicos. El middleware y su validación pertenecen al entorno de producción;
no se ha instalado, simulado ni desplegado un SSO en este proyecto.

`credentials/credentials.json` y `credentials/token.json` permiten al proceso
Python consultar Drive y Sheets como cuenta técnica. **Ese OAuth no identifica
al usuario del navegador ni concede administración**, aunque la cuenta técnica
coincida con la dirección administrativa.

## Comportamiento comprobado

| Identidad entregada por el proveedor verificado | Administración |
|---|---|
| `empleado@crepesywafflesantioquia.com` | Denegada |
| `info.costos@crepesywafflesantioquia.com` | Permitida |
| Misma dirección en mayúsculas o con espacios externos | Permitida tras normalizar |
| Correo vacío o usuario no autenticado | Denegada |

En localhost no hay proveedor corporativo configurado: el botón permanece oculto
y las operaciones administrativas responden 403. No existe una variable de
producción que active un usuario falso o salte esta comprobación.
Las identidades simuladas se definen exclusivamente en `tests/` y sus aplicaciones
usan `TESTING=True`. Esa opción por sí sola tampoco concede permisos.

El botón Administración comienza oculto. `obtenerEstadoAdministrador` lo muestra
solamente si devuelve `esAdministrador=true`; false o error lo mantienen oculto.
El backend vuelve a autorizar consolidado, CSV y plano Siesa mediante
`IdentityService.require_admin` antes de consultar datos. Ocultar o modificar
el botón no cambia los permisos.

Evidencia: `tests/test_identity.py` comprueba los correos anteriores, autorización
de cada endpoint, reevaluación por solicitud, independencia del OAuth y rechazo
de identidad falsificada mediante querystring, JSON, Base64 y encabezados.
`tests/test_frontend.py` comprueba interfaz administrativa, usuario normal,
ausencia de identidad y fallo al consultar el estado.

Pendiente externo: conectar y probar el proveedor corporativo real cuando el
responsable configure producción. Los permisos y su contrato ya están implementados.
