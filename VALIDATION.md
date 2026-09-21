# Estado de validación

## Estado actual — cierre SSO/JWT del 21 de septiembre de 2026

Se retomó el repositorio limpio en e566ab0. La migración tenía 168 pruebas aprobadas
y autorización administrativa mediante IdentityService, pero ningún login JWT,
endpoint de sesión, cookie o timeout. Se revisaron el servicio, controlador,
frontend, configuración y pruebas reales del repositorio local de Uno a Uno.

Implementado exclusivamente lo pendiente de autenticación: POST /auth/sso,
POST /auth/activity, GET/POST /auth/status, POST /auth/logout, GET /auth/expired
y GET /healthz. SSO RS256 con issuer calco-intranet y audience nuevo
inventarios-mensuales; email obligatorio firmado y sesión interna HS256 independiente.
Se conserva IdentityService y la única dirección administrativa del legacy.
Se reutiliza la política de inactividad de Uno a Uno: 1200 segundos, actividad real,
heartbeat de 45 segundos, comprobación de 5 segundos y coordinación entre pestañas.

**Suite completa: 287 aprobadas, 0 fallidas y 0 omitidas, en 35,33 segundos.**
Se conservan las 168 pruebas anteriores y se agregan 119:

| Grupo nuevo | Pruebas | Evidencia |
|---|---:|---|
| SSO, sesión, configuración y frontend de actividad | 117 | tests/test_sso.py y tests/auth_frontend.cjs |
| Expiración y recuperación de borrador en Chromium | 2 | tests/test_sso_browser.py |

La nueva cobertura incluye JWT válido, firma ajena, none/HS256 rechazados para SSO,
issuer/audience incorrectos (incluido Uno a Uno), expiración, nbf futuro, claims
faltantes o inválidos, replay atómico/TTL, email firmado, admin/usuario normal,
normalización, OAuth independiente, cookie HttpOnly/Secure, logout, actividad
deslizante, polling sin renovación, pestañas compartidas y conservación del borrador.
También verifica que una sesión expirada no se renueve ni borre una cookie más nueva.

Las pruebas usan claves RSA efímeras en RAM y servicios Google fake. Se ejecutaron
primero 130 pruebas dirigidas; después pasaron las dos de Chromium y la suite global.
El adaptador del navegador transporta la cookie emitida por el endpoint de prueba;
el 303 SSO se comprueba por separado en Flask test client. No se inició un servidor.

Comando global:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q --junitxml .runtime/sso-validation.xml
```

Dependencias: PyJWT 2.14.0 con cryptography 50.0.1; pip check sin incompatibilidades.
El XML es temporal y sus resultados se conservan aquí. Las mediciones de carga del
18 de septiembre permanecen intactas; los 24 escenarios de concurrencia volvieron
a pasar dentro de la regresión.

La propuesta docs/WOODY_INVENTARIOS_UNIFICADO.php conserva issuer/audience/URL
de Uno a Uno y añade Mensuales mediante whitelist fija. Su compatibilidad se revisó
en el código del validador de Uno a Uno, que admite claims adicionales como email.
El PHP de referencia no se ejecutó localmente ni se publicó en WordPress.
Reemplazo pendiente: __INVENTARIOS_MENSUALES_URL__ por la URL HTTPS base real.
No se generaron claves de producción ni se modificaron paths reales.

Configuración efectiva local comprobada: AUTH_ENABLED=false,
SESSION_IDLE_TIMEOUT_SECONDS=1200 y GOOGLE_WRITES_ENABLED=false.
Pendientes externos: dominio/hosts permitidos, clave pública y secreto de sesión,
configuración autenticada y publicación manual del snippet. ReplayCache conserva
el alcance de un proceso como Uno a Uno; no se afirma protección entre réplicas.
Detalle y contrato en [docs/AUTENTICACION_ADMIN.md](docs/AUTENTICACION_ADMIN.md).

No se cambió lógica de inventario, caché, single-flight, batching, concurrencia,
Guardar, Finalizar, duplicados, total, generador, preparación, CSV, Siesa ni limpieza.
No se consultó ni escribió Google real durante esta tarea. No hubo modificaciones
de WordPress real, deployment, Docker, CI/CD, infraestructura, commit ni push.
run.py no se ejecutó; el inicio continúa siendo exclusivamente manual.
Comprobación final: 0 procesos de aplicación y 0 listeners del proyecto, incluidos
los puertos 5000 y 8000. Se retiró el XML temporal; no quedó ningún servidor iniciado.

## Registro del cierre de migración — 18 de septiembre de 2026

El bloque siguiente conserva la evidencia del cierre anterior. Su pendiente de
implementar identidad corporativa fue atendido por el cierre SSO/JWT documentado arriba;
la configuración y comprobación contra WordPress productivo siguen pendientes.

Revisión del 18 de septiembre de 2026. Se retomó el repositorio existente sin
revertir cambios ni volver a implementar funciones ya probadas.

Último punto realmente completado al retomar: implementación y suite de 151 pruebas
aprobadas. El usuario había completado después el OAuth propio, la lectura real
y la validación manual de Guardar/recuperar borradores. No se repitió implementación.
Faltaban evidencia explícita de identidad administrativa, carga con 40 productos,
cierre documental y comprobación de ausencia de servidores.

Primero se aprobaron 53 pruebas dirigidas. Después se ejecutó la suite completa:
**168 aprobadas, 0 fallidas, 0 omitidas, 31,23 segundos.**
Se añadieron o reforzaron pruebas y documentación; no se cambió código de negocio,
frontend, run.py ni fuentes legacy durante este cierre.

Comando ejecutado:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q --load-report docs/concurrency_results.json --junitxml .runtime/validation.xml
```

El XML es evidencia temporal de la ejecución; sus resultados quedan registrados
aquí y se elimina al cerrar. El JSON de concurrencia se conserva porque permite
revisar las mediciones de los 24 escenarios.

## Resultados por grupo

| Grupo | Aprobadas | Evidencia |
|---|---:|---|
| Caché, single-flight, TTL y retries | 12 | Copias aisladas, expiración, capacidad, errores compartidos y recuperación |
| Concurrencia | 24 | Seis flujos × 10/20/36/40 usuarios |
| Diferenciales contra originales | 47 | Oráculo Node ejecuta los .gs sin modificarlos |
| Frontend Chromium | 12 | DOM, visual exacta, identidad, 429 transitorios/persistentes y escritura incierta |
| Generador y preparación | 6 | XLSX, ZIP, temporales, límite y reanudación sin duplicados |
| Contratos Google | 3 | Construcción oficial de solicitudes, paginación y 429 |
| Identidad administrativa | 10 | Correos autorizados, suplantación, permisos por endpoint y OAuth independiente |
| Inventario, validación, administración y limpieza | 45 | Catálogo, cantidades, duplicados, CSV/Siesa, fechas y llamadas por flujo |
| Seguridad de comandos y bloqueos | 6 | Confirmación de CLI, exclusión entre procesos y app sin abrir sockets |
| Integridad de referencias | 3 | SHA-256, CSS/funciones frontend y matriz completa |
| **Total** | **168** | **Sin fallos ni omisiones** |

Las 47 pruebas diferenciales contienen múltiples casos por función, incluyendo 103
cantidades generadas/dirigidas adicionales para Siesa. Comparan normalización,
códigos, encabezados, unidades, matching, tipos de PDV, nombres, anclas/categorías,
catálogo, fechas, claves, consolidado, CSV completo y plano completo en Base64.
No se declara paridad universal sobre casos o archivos de producción no ejercitados.

## Frontend y visualización

Verificados: carga PDV, fecha inicial, categorías y estados, comienzo, búsqueda,
Cerrado/Abierto, progreso, completar con cero, Guardar sin llamada de escritura,
recuperación tras recargar, Finalizar incompleto/exitoso, categoría deshabilitada,
volver/cambiar PDV, administración, consolidado, filtros y descargas.
Se comprueba conservación del borrador tras error del backend, flush al ocultar
pestaña/cerrar y ocultación administrativa sin identidad.
La identidad normal también oculta Administración, y un fallo al consultar el estado
no la habilita. Las identidades de prueba solo se inyectan en aplicaciones TESTING.

Comparación de PNG renderizados del HTML original frente a la versión Flask:
idénticos en la pantalla de conteo con datos de prueba a 1280×1000 y 390×844.
El CSS es idéntico al extraído del original y se conservan sus 48 funciones.
No se inspeccionó ni operó la web Apps Script de producción.
Los tests interceptan HTTP hacia Flask test client; no levantan servidores.

## Concurrencia y llamadas simuladas

24 escenarios sin fallos inesperados. Las cargas se limitan al aplicativo mensual;
Uno a Uno no se usa simultáneamente.
Los guardados distintos y duplicados utilizan 40 productos por inventario. Se
comprueban las 40 filas completas, encabezados, UUID único por envío, ausencia de
filas cruzadas entre PDV y Total = Cerrado + Abierto.

| Escenario | 36 usuarios | 40 usuarios |
|---|---|---|
| Lecturas compartidas | 36 éxitos, 4 llamadas | 40 éxitos, 4 llamadas |
| Guardados distintos, caché fría | 36 éxitos, 109 llamadas | 40 éxitos, 121 llamadas |
| Misma fecha + PDV + categoría | 1 éxito, 35 duplicados rechazados, 39 llamadas | 1 éxito, 39 duplicados rechazados, 43 llamadas |
| Estados | 36 éxitos, 4 llamadas | 40 éxitos, 4 llamadas |
| Administración/consolidado | 36 éxitos, 1 llamada | 40 éxitos, 1 llamada |
| Borradores locales | 36 éxitos, 0 llamadas | 40 éxitos, 0 llamadas |

Un Finalizar con ID resuelto hace dos llamadas: lectura fresca del libro y
batchUpdate. Los resultados completos, tiempos y espera máxima están en
[docs/CONCURRENCIA_GOOGLE.md](docs/CONCURRENCIA_GOOGLE.md) y su JSON.
Estos fakes no certifican la capacidad ni las cuotas de Google real.

## HTTP 429 y consistencia

Aprobados 429 → 200, 429 → 429 → 200, cuatro 429 persistentes y 5xx transitorios.
Los tres escenarios 429 también recorren Finalizar desde Chromium hasta la política
de reintentos: los transitorios confirman una sola escritura; el persistente conserva
el borrador, rehabilita el botón y no muestra éxito. Una prueba distinta conserva
el borrador cuando la escritura no fue confirmada. Las escrituras no se reintentan.
Los errores 429 se inyectan separadamente de la carga normal.

Los duplicados se comprueban con datos frescos dentro del lock por Spreadsheet.
Probada exclusión entre hilos y entre procesos del mismo host. No se afirma
coordinación entre distintos hosts ni frente a escritores externos.

## Google real en solo lectura

El usuario completó el consentimiento después del intento fallido del cierre
anterior. Cliente y token propio presentes y excluidos de Git; no se copió el token
de Uno a Uno ni se repitió autorización OAuth.

Se repitió `scripts/verify_google_access.py` con el token existente: acceso correcto
a ambas carpetas y a Bases Google - Inventarios Mensuales, 35 PDV, hoja Mensual de
BC01 - Cocina Envigado, 10 categorías y 566 productos, mediante 6 llamadas Google.
El intento dentro del sandbox no obtuvo acceso de red; la ejecución con acceso
autorizado completó la comprobación. No se abrió callback OAuth ni otro listener.
Solo se hicieron consultas de metadatos/listas y lectura de Sheets.

## Pendientes externos y límites de entrega

- Producción debe conectar un proveedor de identidad corporativa verificada.
  La autorización desacoplada ya está implementada y deniega administración sin
  identidad; no se inventó un SSO ni se habilitó acceso para todos.
- No se ejecutaron conversiones, generación, guardado ni limpieza reales en Google.
  Sus pruebas usan fakes. Tampoco se probaron todos los archivos/catálogos reales.
- No hay despliegue ni programación de la limpieza instalados, por instrucción.

## Revisión de repositorio y dependencias

No se encontró AGENTS.md aplicable en el repositorio ni sus directorios superiores.
Se revisaron README, matriz de paridad, validación, fuentes, scripts y pruebas.
Los originales mantienen sus SHA-256 y .gitattributes protege sus bytes.

pip check: No broken requirements found. Las exclusiones de Git cubren cliente,
token, temporales OAuth, .env, claves y archivos de ejecución. No se imprimieron
secretos. La configuración efectiva y .env.example mantienen
`GOOGLE_WRITES_ENABLED=false`. El OAuth técnico no se usa como identidad administrativa.

El repositorio sigue sin staging, commit ni push. git diff --stat muestra solo
README porque los otros archivos del proyecto son nuevos y aún no están en Git;
git status --untracked-files=all muestra el inventario completo.

Inventario final: 78 archivos del proyecto (1 rastreado modificado y 77 nuevos
sin seguimiento; excluye secretos y .venv). De esta tarea son nuevos
docs/AUTENTICACION_ADMIN.md y tests/test_identity.py. Se actualizaron README,
MIGRATION_PARITY, VALIDATION, manuales técnico/usuario, documentación y JSON de carga,
y pruebas existentes de fixtures, concurrencia, frontend, inventario y seguridad.
Se conservaron los demás archivos preparados.

Se eliminaron únicamente caches __pycache__ y el XML temporal de pruebas. No se
inició Flask ni se ejecutó run.py. Se encontró y detuvo el servidor que ya estaba
activo: PID 61904 del entorno de este proyecto y su hijo 41740, que escuchaba
en 127.0.0.1:5000. Las pruebas usaron test client sin servidor; los procesos de
prueba y lectura terminaron. La comprobación final de procesos y listeners no
encontró servidores de este proyecto en 5000, 8000 ni otros puertos.
No se configuró autoarranque, servicio, tarea programada ni inicio desde VS Code.
El usuario inicia la aplicación exclusivamente con `.\.venv\Scripts\python.exe run.py`.
No hubo escritura real en Google, deployment, commit ni push.

## Registro histórico de preparación

El contenido siguiente conserva la primera revisión, anterior a la entrega de
los originales. Sus pendientes no representan el estado actual.

<details>
<summary>Inspección y requisitos registrados inicialmente</summary>

Revisión del 18 de septiembre de 2026. Solo preparación documental y exclusiones
de Git; no existe implementación funcional.

## Inspección inicial

- Leídos completos los dos adjuntos suministrados.
- El repositorio contenía únicamente `README.md` y sus metadatos Git, sin cambios pendientes.
- Los directorios de los dos adjuntos contienen únicamente sus respectivos `pasted-text.txt`.
- No se encontraron los originales mensuales en el repositorio ni entre los archivos
  `.gs` y los HTML de nombre Index de los proyectos hermanos inspeccionados.
- El proyecto hermano InventariosUnoaUno-Temporal sí contiene código propio y una
  referencia de SSO. Se consultó únicamente en lectura; no se modificó ni se reutilizaron
  sus credenciales. Sus pruebas y cifras no validan Inventario Mensual.

## Comprobaciones de preparación realizadas

- Copias de ambos adjuntos verificadas con SHA-256 contra sus archivos de origen:
  - `docs/REQUISITOS_MIGRACION.md`: `BDC01E33C5AF6F74C28890EE23DA913097750693AC5BFC6269D7454047A6AF3E`.
  - `docs/CONTEXTO_CUENTA_GOOGLE.md`: `C3DC78B43F58D21508BC80E5A9178056B01449CF9A98D81A9ACB60565C135E06`.
- `git check-ignore` confirmó las once exclusiones requeridas y que
  `credentials/.gitkeep` puede incluirse en Git. No se crearon secretos de prueba.
- `git diff --check` no reportó errores de whitespace en el cambio de README.
- Preparación: ocho archivos nuevos y un README actualizado. Ninguno está staged.
- `git diff --stat` muestra únicamente README porque los ocho archivos nuevos aún
  no están registrados en Git; `git status` también muestra esos archivos nuevos.

## Pruebas pendientes

| Verificación | Estado |
|---|---|
| Unitarias | No ejecutadas: implementación pendiente |
| Diferenciales contra Apps Script/JavaScript | No ejecutadas: faltan fuentes originales |
| Frontend y comparación visual | No ejecutadas: falta Index.html original |
| Concurrencia de lecturas, finalizaciones distintas y duplicadas, 10/20/36/40 usuarios | No ejecutada |
| Recuperación 429 → 200 y 429 → 429 → 200 | No ejecutada |
| Cuatro 429 consecutivos, error controlado y borrador conservado | No ejecutada |
| Llamadas Google por flujo y por Finalizar | Sin medición; no se estiman a partir de otro aplicativo |
| Google real en solo lectura | No ejecutada; script pendiente |
| Generación, preparación de bases y limpieza con fakes | No ejecutadas |

## Pendientes para continuar

1. Recibir las tres fuentes indicadas en `legacy/README.md` y conservar copias exactas.
2. Leer e inventariar todo el legacy antes de programar.
3. Implementar MVC, servicios Google, identidad/autorización desacoplada y comandos administrativos.
4. Ejecutar las pruebas solicitadas y registrar mediciones propias del aplicativo mensual.
5. Completar `docs/MANUAL_USUARIO.md`, `docs/FUNCIONAMIENTO_SISTEMA.md` y la documentación técnica.
6. Verificar Google solo en lectura tras implementar y disponer del OAuth de este proyecto.

## Operaciones externas

No se realizaron llamadas ni escrituras a Google. No se generaron bases, carpetas,
ZIP, conversiones, conteos ni limpiezas reales. No se hizo despliegue, commit ni push.
No se inició ningún servidor ni proceso de aplicación.

</details>
