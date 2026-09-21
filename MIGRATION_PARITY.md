# Paridad de migración

## Estado actual tras recibir las fuentes

Leídos y preservados completos los dos .gs y el HTML. SHA-256 en legacy/SHA256.json.
La matriz cubre las 42 funciones del generador, las 42 de la web Apps Script y las
48 del frontend. No se declara paridad absoluta sobre todos los archivos reales.

**D**: casos diferenciales contra JavaScript original (incluye funciones ejercitadas
por un flujo mayor). **F**: prueba funcional con fakes/Chromium; sin comparación
diferencial completa. **R**: sustitución técnica del runtime Apps Script.
La combinación indica ambos tipos de evidencia, no una validación de producción.
La columna Prueba identifica el archivo o escenario; las funciones auxiliares pueden
estar cubiertas por un flujo compartido. Una revisión técnica R no equivale a
una prueba diferencial. Las escrituras reales siguen deshabilitadas.

### Generador

| Apps Script | Python | Prueba / evidencia | Estado |
|---|---|---|---|
| `iniciarGeneracion` | MonthlyGeneratorService.run | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F/R: checkpoint local y ejecución secuencial |
| `continuarGeneracion` | MonthlyGeneratorService.run | tests/test_generator.py::test_generator_interruption_after_upload_resumes_without_duplicate | F/R: reanuda sin trigger |
| `procesarPdv_` | MonthlyGeneratorService.process_pdv | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F |
| `extraerProductosActualizados_` | generator_rules.extract_products | tests/test_differential.py (flujo de reglas del generador) | D/F |
| `obtenerCategoriasPorCodigo_` | generator_rules.categories_by_code | tests/test_differential.py (flujo de reglas del generador) | D/F |
| `detectarTablaCategorias_` | generator_rules.detect_category_table | tests/test_differential.py (flujo de reglas del generador) | D |
| `asignarCategoriasDesdeTabla_` | generator_rules.assign_table | tests/test_differential.py (flujo de reglas del generador) | D por categories_by_code |
| `detectarAnclasCategorias_` | generator_rules.detect_anchors | tests/test_differential.py (flujo de reglas del generador) | D |
| `agregarAnclaCategoria_` | generator_rules.add_anchor | tests/test_differential.py (flujo de reglas del generador) | D por detect_anchors |
| `categoriaParaCelda_` | generator_rules.category_for_cell | tests/test_differential.py (flujo de reglas del generador) | D |
| `categoriaEnMismaFila_` | generator_rules.same_row_category | tests/test_differential.py (flujo de reglas del generador) | D |
| `distanciaAColumna_` | generator_rules.column_distance | tests/test_differential.py (flujo de reglas del generador) | D por selección de anclas |
| `esCategoriaCandidata_` | generator_rules.category_candidate | tests/test_differential.py (flujo de reglas del generador) | D |
| `limpiarCategoria_` | generator_rules.clean_category | tests/test_differential.py (flujo de reglas del generador) | D |
| `construirFilasSalida_` | generator_rules.output_rows | tests/test_differential.py (flujo de reglas del generador) | D |
| `generarExcel_` | monthly_generator.build_xlsx | tests/test_generator.py::test_real_xlsx_format_and_text | F/R: XLSX openpyxl en memoria |
| `exportarComoXlsx_` | monthly_generator.build_xlsx | tests/test_generator.py::test_real_xlsx_format_and_text | F/R: no requiere exportar un Sheet temporal |
| `crearZipFinal_` | MonthlyGeneratorRepository.zip_outputs | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F |
| `detectarColumnas_` | generator_rules.detect_columns | tests/test_differential.py (flujo de reglas del generador) | D |
| `separarUnidadEmpaque_` | generator_rules.split_pack | tests/test_differential.py (flujo de reglas del generador) | D |
| `normalizarUnidad_` | generator_rules.normalize_unit | tests/test_differential.py (flujo de reglas del generador) | D |
| `normalizarCodigo_` | generator_rules.normalize_code | tests/test_differential.py (flujo de reglas del generador) | D |
| `codigosPosiblesEnCelda_` | generator_rules.possible_codes | tests/test_differential.py (flujo de reglas del generador) | D |
| `buscarMejorFormato_` | generator_rules.best_template | tests/test_differential.py (flujo de reglas del generador) | D |
| `puntajeCoincidencia_` | generator_rules.match_score | tests/test_differential.py (flujo de reglas del generador) | D |
| `claveNombre_` | generator_rules.name_key | tests/test_differential.py (flujo de reglas del generador) | D |
| `tipoPdv_` | generator_rules.pdv_type | tests/test_differential.py (flujo de reglas del generador) | D |
| `listarArchivos_` | MonthlyGeneratorRepository.files | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F |
| `quitarDuplicadosFormatos_` | generator_rules.deduplicate_templates | tests/test_differential.py (flujo de reglas del generador) | D |
| `abrirArchivoComoHoja_` | MonthlyGeneratorRepository.open_book | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F: conversión real no ejecutada |
| `cerrarTemporal_` | finally de MonthlyGeneratorRepository.open_book | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F |
| `buscarHoja_` | generator_rules.extract_products / models.sheets.find_sheet | tests/test_differential.py (flujo de reglas del generador) | D/F |
| `esEncabezadoCodigo_` | generator_rules.code_header | tests/test_differential.py (flujo de reglas del generador) | D por detect_columns |
| `esEncabezadoProducto_` | generator_rules.product_header | tests/test_differential.py (flujo de reglas del generador) | D por detect_columns |
| `esEncabezadoUnidad_` | generator_rules.unit_header | tests/test_differential.py (flujo de reglas del generador) | D por detect_columns |
| `normalizarTexto_` | models.text.generator_normalize | tests/test_differential.py (flujo de reglas del generador) | D |
| `crearNombreSalida_` | generator_rules.output_name | tests/test_differential.py (flujo de reglas del generador) | D |
| `limpiarNombreArchivo_` | generator_rules.safe_output_name | tests/test_differential.py (flujo de reglas del generador) | D |
| `aplicarFilasAlternas_` | monthly_generator.build_xlsx | tests/test_generator.py::test_real_xlsx_format_and_text | F |
| `eliminarTriggersContinuacion_` | Sin triggers; secuencia y lock del generador | Revisión de scripts; no existen triggers | R |
| `verEstado` | MonthlyGeneratorService.status / CLI sin --execute | tests/test_generator.py::test_generator_full_run_resume_zip_and_temporaries | F/R |
| `reiniciarEstado` | MonthlyGeneratorService.reset / --reset-state --confirm | tests/test_generator.py::test_explicit_reset_same_minute_does_not_reuse_stale_results | R |

### Web Apps Script

| Apps Script | Python | Prueba / evidencia | Estado |
|---|---|---|---|
| `prepararBasesMensuales` | MonthlyPreparationService.run | tests/test_generator.py::test_preparation_limit_existing_and_invalid | F: límite de intentos documentado |
| `obtenerOCrearCarpetaBases_` | preparación + MonthlyBasesRepository.folder | tests/test_generator.py::test_preparation_limit_existing_and_invalid | F/R: lectura no crea carpetas |
| `existeHojaGoogle_` | MonthlyPreparationService.run | tests/test_generator.py::test_preparation_limit_existing_and_invalid | F |
| `buscarHoja_` | models.sheets.find_sheet | tests/test_differential.py | D/F |
| `normalizar_` | models.text.normalize | tests/test_differential.py | D |
| `doGet` | controllers.web.index | tests/test_frontend.py::test_original_visual_parity | F: comparación visual escritorio/móvil |
| `obtenerEstadoAdministrador` | RPC + IdentityService.is_admin | tests/test_identity.py; tests/test_frontend.py | F |
| `obtenerCorreoUsuario_` | IdentityService.username + sesión SSO verificada | tests/test_identity.py; tests/test_sso.py | R: cambio solicitado a user_login firmado en sub y ADMIN_USER_LOGINS configurable |
| `esCorreoAdministrador_` | IdentityService.is_admin | tests/test_identity.py; tests/test_frontend.py | F |
| `validarAccesoAdministrador_` | IdentityService.require_admin | tests/test_identity.py; tests/test_frontend.py | F |
| `obtenerCarpetaBasesMensuales_` | MonthlyBasesRepository.folder | tests/test_inventory.py; tests/test_concurrency.py | F/R |
| `obtenerPuntosVenta` | MonthlyBasesRepository.points | tests/test_inventory.py; tests/test_concurrency.py | F |
| `obtenerCategorias` | MonthlyInventoryService.categories | tests/test_inventory.py; tests/test_concurrency.py | F |
| `obtenerProductos` | MonthlyBasesRepository.products / products_from_book | tests/test_differential.py | D/F |
| `obtenerEstadoCategoriasMensuales` | MonthlyInventoryService.states | tests/test_inventory.py; tests/test_concurrency.py | F |
| `guardarInventario` | MonthlyInventoryService.finalize | tests/test_inventory.py; tests/test_concurrency.py (40 productos) | F: concurrencia, integridad y bloqueo |
| `validarInventarioMensual_` | monthly_inventory.validate_payload | tests/test_inventory.py; tests/test_concurrency.py | F: validación reforzada |
| `obtenerLibroMensualPDV_` | MonthlyBasesRepository.resolve | tests/test_inventory.py; tests/test_concurrency.py | F |
| `validarIntegridadConteosMensuales_` | monthly_inventory.validate_integrity | tests/test_inventory.py (catálogo fresco, alterado, faltante y repetido) | F: multiconjunto y catálogo fresco |
| `crearClaveProductoMensual_` | models.text.product_key | tests/test_differential.py | D |
| `crearClaveCacheMensual_` | Claves tuple de ReadCache | tests/test_cache_retry.py; tests/test_concurrency.py | R: sin MD5 ni límite de Apps Script |
| `categoriaMensualYaGuardada_` | monthly_inventory.is_duplicate | tests/test_inventory.py; tests/test_concurrency.py (40 productos) | F: siempre lee Google fresco |
| `generarDescargaConteosMensuales` | MonthlyAdminService.csv | tests/test_differential.py | D/F: contenido Base64 completo |
| `generarPlanoSiesaMensual` | MonthlyAdminService.flat / flat_file | tests/test_differential.py | D/F: contenido Base64 completo |
| `formatearItemPlanoSiesa_` | monthly_admin.item_flat | tests/test_differential.py | D |
| `formatearCantidadPlanoSiesa_` | monthly_admin.quantity_flat | tests/test_differential.py | D: casos dirigidos y generados |
| `convertirNumeroPlanoSiesa_` | models.text.parse_number | tests/test_differential.py | D |
| `nombrePDVPlanoSiesa_` | monthly_admin.pdv_flat | tests/test_differential.py | D |
| `obtenerConteoConsolidadoPDV` | MonthlyAdminService.consolidated / consolidate | tests/test_differential.py | D/F |
| `redondearConteoMensual_` | models.text.rounded_count | tests/test_differential.py | D |
| `formatearItemSiesa_` | monthly_admin.item_siesa | tests/test_differential.py | D |
| `escaparCampoCSV_` | monthly_admin.csv_field | tests/test_differential.py | D |
| `nombreArchivoSeguro_` | models.text.safe_filename | tests/test_differential.py | D |
| `prepararEncabezadosMensuales_` | MonthlyInventoryRepository.append | tests/test_inventory.py; tests/test_concurrency.py | F: creación inicial en batch |
| `buscarIndiceMensual_` | monthly_bases.find_index | tests/test_differential.py | D |
| `limpiarTextoMensual_` | models.text.clean | tests/test_differential.py | D |
| `claveFechaMensual_` | models.text.date_key | tests/test_differential.py | D: cadenas; fechas tipadas con F |
| `probarConexionMensual` | scripts/verify_google_access.py | scripts/verify_google_access.py (lectura real: 6 llamadas) | R: OAuth propio y lectura real verificados |
| `probarProductosMensuales` | verify_google_access.py + pruebas de catálogo | scripts/verify_google_access.py (lectura real: 6 llamadas) | F/R: no fija un PDV nuevo |
| `instalarLimpiezaAutomaticaMensual` | Instrucciones de programación de CLI en manual técnico | Revisión de scripts; ninguna tarea instalada | R: programación no instalada |
| `limpiarConteosMensualesVencidos` | MonthlyCleanupService.run | tests/test_inventory.py::test_cleanup_preserves_invalid_exact_boundary_and_catalog | F: límites, inválidas y dry-run |
| `desinstalarLimpiezaAutomaticaMensual` | Desactivar tarea que cree el operador | Revisión de scripts; ninguna tarea instalada | R: no hay trigger Python instalado |

### Frontend

Todas conservan su nombre en app/static/js/monthly.js. El transporte se adapta con
monthlyApi, y los eventos con events.js. CSS copiado exactamente. **F** corresponde
a cobertura de flujos en Chromium; no se afirma una prueba aislada por cada helper.

| Apps Script / Index.html | Python / frontend Flask | Prueba / evidencia | Estado |
|---|---|---|---|
| `asignarFechaActual` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `cargarPuntosVenta` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `verificarAdministrador` | monthly.js / misma función | tests/test_frontend.py (admin, usuario normal, sin identidad y error) | F |
| `cargarPuntosAdministrador` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `abrirAdministracion` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `cerrarAdministracion` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `abrirConteoConsolidado` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `filtrarConteoConsolidado` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `renderizarConteoConsolidado` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `agregarCeldaConteo` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `actualizarResumenConteo` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `volverAdministracion` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `normalizarBusqueda` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `formatearNumeroConteo` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `formatearFechaVisible` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `descargarConteosMensuales` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `descargarPlanoSiesaMensual` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `descargarArchivoBase64` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `cargarCategoriasPDV` | monthly.js / misma función, descarte de respuestas antiguas | tests/test_frontend.py (flujos DOM compartidos) | F/R |
| `calcularEstadoCategoria` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `etiquetaEstadoCategoria` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `mostrarEstadoCategorias` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `comenzarInventario` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `cargarCategoriaInventario` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `prepararInventario` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `mostrarProductos` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `programarMostrarProductos` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `registrarCantidad` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `programarActualizacionProgreso` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `actualizarProgreso` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `completarVaciosConCero` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `guardarProceso` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `finalizarInventario` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `actualizarCategoriaGuardadaEnSelector` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `volverMenuCategorias` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `nuevoInventario` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `guardarBorrador` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `guardarBorradorAhora` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `recuperarBorrador` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `eliminarBorrador` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `obtenerClaveBorrador` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `obtenerClaveBorradorPara` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `mostrarMensaje` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `ocultarMensaje` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `obtenerMensajeError` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `formatearFecha` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `normalizarTexto` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |
| `escaparHTML` | monthly.js / misma función | tests/test_frontend.py (flujos DOM compartidos) | F |

### Adaptaciones técnicas y límites explícitos

- Fecha calendario real y rechazo de números no finitos/booleanos en backend.
- Catálogo fresco al Finalizar, además de la comprobación fresca de duplicados.
- Creación de carpetas reservada a comandos administrativos.
- Sin triggers Apps Script, ni límite artificial de cuatro minutos; checkpoint local.
- Límite de preparación cuenta intentos para limitar llamadas fallidas.
- El ZIP se actualiza por ID cuando existe, en vez de mandarlo a papelera y recrearlo.
- Nuevos XLSX producidos localmente, conservando contenido/estilo; no identidad binaria
  con el archivo exportado por Google, que usa otro motor.
- Bloqueo en un host, no transacción distribuida con el Apps Script original.
- Identidad corporativa desacoplada y denegación administrativa sin proveedor verificado.
- OAuth propio y lectura real verificados: 35 PDV, Mensual BC01, 566 productos, 6 llamadas.
- SSO WordPress/JWT implementado y probado con RSA efímera, sesión de 1200 segundos
  de inactividad y borrador conservado. Contrato en docs/AUTENTICACION_ADMIN.md.
- Conversiones/escrituras reales, SSO productivo y datasets completos de producción no validados.


## Registro histórico de preparación, ya superado

La lista siguiente corresponde a la primera entrega, antes de recibir las fuentes.
El estado vigente es la matriz anterior.

<details>
<summary>Matriz preliminar, conservada como historial</summary>

Estado al 18 de septiembre de 2026: ninguna función migrada ni paridad comprobada.
Faltan los dos archivos Apps Script y el HTML original. Esta lista recoge únicamente
los nombres citados en los requisitos; no constituye un inventario completo del legacy.
La columna Python se completará con las funciones efectivamente implementadas.

| Apps Script | Python | Estado |
|---|---|---|
| `iniciarGeneracion` | Pendiente | Fuente original no recibida |
| `separarUnidadEmpaque_` | Pendiente | Fuente original no recibida |
| `normalizarUnidad_` | Pendiente | Fuente original no recibida |
| `detectarTablaCategorias_` | Pendiente | Fuente original no recibida |
| `asignarCategoriasDesdeTabla_` | Pendiente | Fuente original no recibida |
| `detectarAnclasCategorias_` | Pendiente | Fuente original no recibida |
| `categoriaParaCelda_` | Pendiente | Fuente original no recibida |
| `categoriaEnMismaFila_` | Pendiente | Fuente original no recibida |
| `esCategoriaCandidata_` | Pendiente | Fuente original no recibida |
| `limpiarCategoria_` | Pendiente | Fuente original no recibida |
| `buscarMejorFormato_` | Pendiente | Fuente original no recibida |
| `puntajeCoincidencia_` | Pendiente | Fuente original no recibida |
| `claveNombre_` | Pendiente | Fuente original no recibida |
| `tipoPdv_` | Pendiente | Fuente original no recibida |
| `prepararBasesMensuales` | Pendiente | Fuente original no recibida |
| `obtenerCategorias` | Pendiente | Fuente original no recibida |
| `validarIntegridadConteosMensuales_` | Pendiente | Fuente original no recibida |
| `obtenerConteoConsolidadoPDV` | Pendiente | Fuente original no recibida |
| `generarDescargaConteosMensuales` | Pendiente | Fuente original no recibida |
| `generarPlanoSiesaMensual` | Pendiente | Fuente original no recibida |
| `limpiarConteosMensualesVencidos` | Pendiente | Fuente original no recibida |
| Interfaz y funciones de `Index.html` | Pendiente | HTML/CSS/JavaScript original no recibido |

Quedan pendientes el inventario completo de funciones, las pruebas diferenciales,
la comparación visual y la verificación de los casos límite del original.

</details>
