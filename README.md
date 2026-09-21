# Inventarios Mensuales PDV

Migración solicitada de los proyectos Apps Script «Generador Inventario Mensual» e
«Inventarios Mensuales PDV» a Python y Flask, manteniendo Google Drive y Google
Sheets como fuente de verdad.

**Estado actual: migración implementada, con pruebas diferenciales, fakes y Chromium.
Los tres originales permanecen intactos en legacy. OAuth propio y lectura real
verificados: 35 PDV y 566 productos de BC01 en 6 llamadas. SSO WordPress RS256 y
sesión interna implementados con la misma inactividad de Uno a Uno: 1200 segundos.
Falta configurar claves/dominio y publicar manualmente el snippet en producción.**

## Instalación y ejecución local

Requiere Python 3.12 o posterior y la biblioteca ICU del sistema para ordenar en
español como JavaScript Intl. Windows 10/11 incluye icu.dll; en Linux instalar ICU
mediante el administrador de paquetes del sistema. Node se usa solo en pruebas.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La aplicación solo queda disponible cuando el usuario ejecuta manualmente:

```powershell
.\.venv\Scripts\python.exe run.py
```

El entorno .venv ya quedó creado en este equipo. Si Python no está en PATH, se puede
usar directamente ese intérprete. Abrir http://127.0.0.1:5000. No hay depurador ni
reinicio automático; detener con Ctrl+C. No se dejó un servidor ejecutándose.
No iniciar Flask como parte de pruebas, instalación, apertura de VS Code o tareas
del asistente. No hay servicios, tareas programadas ni autoarranque configurados.

Opcionalmente copiar .env.example a .env. Por defecto las escrituras Google están
deshabilitadas. El operador debe autorizar su uso y configurar
GOOGLE_WRITES_ENABLED=true para permitir Finalizar contra los datos reales.
Guardar borrador siempre es local y no requiere esa opción.

## OAuth y verificación en solo lectura

El cliente OAuth permitido de Inventario Uno a Uno está en credentials/credentials.json,
excluido de Git. El usuario ya autorizó el token propio credentials/token.json;
no se copió el token del otro aplicativo ni hace falta repetir el consentimiento.
Para comprobar el acceso existente, sin iniciar servidores:

```powershell
.\.venv\Scripts\python.exe scripts/verify_google_access.py
```

Solo si falta o se revoca el token, el operador puede iniciar explícitamente
el consentimiento con el mismo script y `--authorize`. Ese flujo OAuth interactivo
usa un callback local temporal; no se ejecuta automáticamente.
El verificador nunca escribe datos, convierte archivos ni crea carpetas en Google.
Utiliza scopes de Sheets y Drive; sin Forms ni Service Account.
El OAuth identifica a la cuenta técnica que accede a archivos; no autentica al
usuario del navegador ni le concede administración.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --load-report docs/concurrency_results.json
.\.venv\Scripts\python.exe -m pip check
```

Las pruebas de navegador usan Chrome local. Si no está instalado:
`python -m playwright install chromium`. Interceptan todo HTTP hacia Flask test
client: no abren puertos ni llaman a Google. Las pruebas diferenciales ejecutan
los originales en Node sin servicios Apps Script reales.

## Operaciones administrativas

Sin estos indicadores explícitos no se autoriza escribir:

```powershell
# Estado local; no llama a Google
.\.venv\Scripts\python.exe scripts/generate_monthly_bases.py
# Genera/reanuda, SOLO cuando el operador autorice escrituras reales
.\.venv\Scripts\python.exe scripts/generate_monthly_bases.py --execute --confirm --limit 5
# Convierte como máximo 5 archivos por invocación
.\.venv\Scripts\python.exe scripts/prepare_monthly_bases.py --execute --confirm
# Simulación de limpieza, solo lectura
.\.venv\Scripts\python.exe scripts/cleanup_monthly_counts.py --dry-run
# Limpieza real, SOLO cuando esté autorizada
.\.venv\Scripts\python.exe scripts/cleanup_monthly_counts.py --execute --confirm
```

El generador conserva su progreso en .runtime/generator.json. Repetir el comando
continúa el trabajo; --reset-state --confirm elimina únicamente ese estado local.
La limpieza se coordina con Finalizar mediante bloqueos por Spreadsheet.
No se instaló ningún programador de tareas ni se modificó despliegue.

## Arquitectura implementada

```text
app/controllers/       HTTP, errores, encabezados de seguridad
app/models/            reglas puras, estructuras y conversión de celdas
app/repositories/      bases, conteos y archivos del generador
app/services/          inventario, administración, limpieza, generador,
                       OAuth, Drive, Sheets, identidad, caché, retries y locks
app/templates/         HTML del original, adaptado a Flask
app/static/            CSS original y JavaScript con transporte HTTP
scripts/               comandos y extracción reproducible del frontend
tests/                 fakes, pruebas diferenciales, carga y Chromium
legacy/                originales inmutables y SHA-256
docs/                  requisitos, manuales y resultados
credentials/           cliente y token OAuth excluidos de Git
```

La administración deniega por defecto. Con AUTH_ENABLED=true, POST /auth/sso
valida JWT RS256 del emisor calco-intranet para inventarios-mensuales y conecta
IdentityService al `user_login` firmado en `sub` de la sesión interna. Los administradores
se configuran únicamente en `.env` mediante `ADMIN_USER_LOGINS`, separados por comas,
con trim y minúsculas. Vacío significa que nadie es administrador; no hay usuarios
predeterminados en el backend. Un login puede tener formato de correo, pero debe coincidir
con `user_login`, no con `user_email`. No se acepta identidad por querystring, encabezados
arbitrarios ni OAuth técnico. La lista se carga al iniciar la aplicación.
El contrato está en [Autenticación administrativa](docs/AUTENTICACION_ADMIN.md).

## SSO y sesión

La configuración local mantiene AUTH_ENABLED=false y GOOGLE_WRITES_ENABLED=false.
La preparación SSO está en .env.example: clave pública RSA y secreto interno propio
pendientes de suministrar por el operador. Producción exige autenticación y cookie
Secure. No se generaron claves reales ni se modificó WordPress.

SESSION_IDLE_TIMEOUT_SECONDS=1200 mide inactividad real. Escribir, hacer clic,
desplazarse o mover el ratón mantiene la sesión mediante actividad limitada a un
envío cada 45 segundos. Los sondeos, las consultas API y una pestaña abierta sin
actividad no renuevan por sí solos. El borrador se conserva al expirar.

[Snippet Woody unificado de referencia](docs/WOODY_INVENTARIOS_UNIFICADO.php):
conserva Uno a Uno y añade Mensuales. Sustituir __INVENTARIOS_MENSUALES_URL__ por
la URL HTTPS base real, sin barra final ni /auth/sso. No hay dominio mensual asumido.
No ejecutar ese archivo localmente; el usuario lo copiará al mismo snippet Woody.

## Documentación de la implementación

- [Manual de usuario y administración](docs/MANUAL_USUARIO.md).
- [Funcionamiento técnico](docs/FUNCIONAMIENTO_SISTEMA.md).
- [Autenticación administrativa](docs/AUTENTICACION_ADMIN.md).
- [Concurrencia Google](docs/CONCURRENCIA_GOOGLE.md).
- [Matriz de paridad](MIGRATION_PARITY.md).
- [Validación y límites](VALIDATION.md).

## Registro de preparación inicial

El texto siguiente documenta la fase anterior a recibir los tres originales.
Sus pendientes quedaron reemplazados por el estado actual indicado arriba.

<details>
<summary>Documentación conservada de la preparación inicial</summary>

## Fuentes necesarias

Los dos adjuntos recibidos contienen requisitos, pero no el código original.
Antes de programar se necesitan copias exactas de:

| Proyecto de origen | Archivo original | Destino en este repositorio |
|---|---|---|
| Generador Inventario Mensual | Código.gs | `legacy/generador_inventario_mensual.gs` |
| Inventarios Mensuales PDV | Código.gs | `legacy/inventarios_mensuales_pdv.gs` |
| Inventarios Mensuales PDV | Index.html | `legacy/index_original.html` |

La condición procede del apartado 2 de los requisitos: «Antes de programar: Lee
TODO el material suministrado del Apps Script original». No se han creado archivos
de código sustitutivos. Los algoritmos de categorías y emparejamiento, las posiciones
del plano Siesa y la interfaz requieren esas fuentes para comprobar la paridad.

## Arquitectura solicitada, todavía no implementada

Navegador → HTML/CSS/JavaScript → controladores Flask → servicios → repositorios
→ APIs oficiales de Google → Drive/Sheets.

Sin base de datos adicional. El inventario mensual utiliza `Total = Cerrado + Abierto`.
Guardar conserva el borrador en localStorage; Finalizar escribe en `Conteos Mensuales`.

Inventario Uno a Uno e Inventario Mensual usarán la misma cuenta Google, pero no
se ejecutarán simultáneamente. Las pruebas del aplicativo mensual deberán cubrir
10, 20, 36 y 40 usuarios, con caché TTL, single-flight, operaciones agrupadas,
reintentos limitados y protección contra duplicados desde la implementación inicial.

## Credenciales

Rutas previstas: `credentials/credentials.json` y `credentials/token.json`, ambas
excluidas de Git. Puede reutilizarse el cliente OAuth de Inventario Uno a Uno; el
token de esta aplicación debe ser independiente. No se han copiado credenciales,
iniciado OAuth ni realizado llamadas a Google.

## Documentación disponible

- [Requisitos de migración recibidos](docs/REQUISITOS_MIGRACION.md), copia exacta del primer adjunto.
- [Contexto de la cuenta Google](docs/CONTEXTO_CUENTA_GOOGLE.md), copia exacta del segundo adjunto.
- [Fuentes originales pendientes](legacy/README.md).
- [Registro de paridad pendiente](MIGRATION_PARITY.md).
- [Estado de validación](VALIDATION.md).
- [Requisitos de concurrencia](docs/CONCURRENCIA_GOOGLE.md).

Instalación, ejecución, comandos administrativos, manual de usuario y documentación
técnica se completarán junto con la implementación y sus pruebas. Actualmente no
existen `run.py`, dependencias instaladas ni scripts administrativos ejecutables.

## Límites de esta fase

No ejecutar operaciones de escritura sobre Google durante el desarrollo sin
autorización explícita. La verificación real prevista será solo de lectura y
posterior a la implementación. No se ha realizado despliegue, commit ni push.

</details>
