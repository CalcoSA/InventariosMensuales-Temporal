const CONFIG = {
  CARPETA_MENSUAL_ID: '1DwPotMtT1Y-V4qIuob3TXmWjfAc2tbWm',
  CARPETA_FORMATOS_ID: '1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk',
  HOJAS_FUENTE: ['Pedido Diario', 'Bodega'],
  HOJAS_CATEGORIAS: ['Mensual', 'Formato de Inventario Mensual'],
  NOMBRE_CARPETA_SALIDA: 'RESULTADOS INVENTARIO MENSUAL',
  COLOR_CAFE: '#6B3F2A',
  COLOR_CREMA: '#F3E9DC',
  LIMITE_MS_POR_EJECUCION: 240000
};

/**
 * FUNCIÓN PRINCIPAL.
 * Ejecutar una sola vez para iniciar todo el proceso.
 */
function iniciarGeneracion() {
  const bloqueo = LockService.getScriptLock();
  bloqueo.waitLock(30000);

  try {
    eliminarTriggersContinuacion_();

    const propiedades = PropertiesService.getScriptProperties();
    propiedades.deleteAllProperties();

    const carpetaMensual = DriveApp.getFolderById(CONFIG.CARPETA_MENSUAL_ID);
    const carpetaFormatos = DriveApp.getFolderById(CONFIG.CARPETA_FORMATOS_ID);

    const mensuales = listarArchivos_(carpetaMensual)
      .filter(a => /09\s*\.xlsx$/i.test(a.nombre));

    const formatos = quitarDuplicadosFormatos_(listarArchivos_(carpetaFormatos));

    if (mensuales.length === 0) {
      throw new Error('No se encontraron archivos .xlsx terminados en 09.');
    }

    if (formatos.length === 0) {
      throw new Error('No se encontraron archivos en la carpeta de formatos.');
    }

    const marcaTiempo = Utilities.formatDate(
      new Date(),
      Session.getScriptTimeZone(),
      'yyyy-MM-dd HH-mm'
    );

    const carpetaSalida = carpetaMensual.createFolder(
      CONFIG.NOMBRE_CARPETA_SALIDA + ' ' + marcaTiempo
    );

    propiedades.setProperties({
      ESTADO: 'EN PROCESO',
      INDICE: '0',
      TOTAL: String(mensuales.length),
      ARCHIVOS_MENSUALES: JSON.stringify(mensuales),
      ARCHIVOS_FORMATOS: JSON.stringify(formatos),
      CARPETA_SALIDA_ID: carpetaSalida.getId(),
      ERRORES: JSON.stringify([]),
      INICIO: new Date().toISOString()
    });

    console.log('Archivos mensuales encontrados: ' + mensuales.length);
    console.log('Formatos encontrados: ' + formatos.length);
    console.log('Carpeta de resultados: ' + carpetaSalida.getUrl());

  } finally {
    bloqueo.releaseLock();
  }

  continuarGeneracion();
}

/**
 * Procesa tantos PDV como permita el tiempo de Apps Script.
 * Si quedan pendientes, crea automáticamente una nueva ejecución.
 */
function continuarGeneracion() {
  const bloqueo = LockService.getScriptLock();

  if (!bloqueo.tryLock(10000)) {
    console.log('Ya existe otra ejecución trabajando.');
    return;
  }

  try {
    eliminarTriggersContinuacion_();

    const inicio = Date.now();
    const propiedades = PropertiesService.getScriptProperties();
    const estado = propiedades.getProperty('ESTADO');

    if (!estado) {
      throw new Error('Primero debes ejecutar iniciarGeneracion.');
    }

    if (estado === 'COMPLETADO') {
      console.log('El proceso ya está completado.');
      verEstado();
      return;
    }

    const mensuales = JSON.parse(
      propiedades.getProperty('ARCHIVOS_MENSUALES') || '[]'
    );

    const formatos = JSON.parse(
      propiedades.getProperty('ARCHIVOS_FORMATOS') || '[]'
    );

    const carpetaSalida = DriveApp.getFolderById(
      propiedades.getProperty('CARPETA_SALIDA_ID')
    );

    let indice = Number(propiedades.getProperty('INDICE') || 0);
    let errores = JSON.parse(propiedades.getProperty('ERRORES') || '[]');

    while (
      indice < mensuales.length &&
      Date.now() - inicio < CONFIG.LIMITE_MS_POR_EJECUCION
    ) {
      const mensual = mensuales[indice];

      console.log(
        'Procesando ' + (indice + 1) + ' de ' + mensuales.length +
        ': ' + mensual.nombre
      );

      try {
        procesarPdv_(mensual, formatos, carpetaSalida);
        console.log('OK: ' + mensual.nombre);

      } catch (error) {
        const mensaje = mensual.nombre + ': ' + error.message;
        errores.push(mensaje);
        console.error('ERROR: ' + mensaje);
      }

      indice++;

      propiedades.setProperties({
        INDICE: String(indice),
        ERRORES: JSON.stringify(errores),
        ULTIMA_ACTUALIZACION: new Date().toISOString()
      });
    }

    if (indice < mensuales.length) {
      propiedades.setProperty('ESTADO', 'PENDIENTE DE CONTINUAR');

      ScriptApp.newTrigger('continuarGeneracion')
        .timeBased()
        .after(60000)
        .create();

      console.log(
        'Avance: ' + indice + ' de ' + mensuales.length +
        '. Continuará automáticamente.'
      );

      return;
    }

    propiedades.setProperty('ESTADO', 'CREANDO ZIP');

    const zip = crearZipFinal_(carpetaSalida);

    propiedades.setProperties({
      ESTADO: 'COMPLETADO',
      ZIP_ID: zip.getId(),
      ZIP_URL: zip.getUrl(),
      FIN: new Date().toISOString()
    });

    eliminarTriggersContinuacion_();

    console.log('PROCESO COMPLETADO');
    console.log('ZIP FINAL: ' + zip.getUrl());

    if (errores.length > 0) {
      console.log('Archivos con novedad: ' + errores.length);
      errores.forEach(error => console.log(error));
    }

  } finally {
    bloqueo.releaseLock();
  }
}

function procesarPdv_(mensual, formatos, carpetaSalida) {
  const formato = buscarMejorFormato_(mensual.nombre, formatos);

  if (!formato) {
    throw new Error('No se encontró un formato correspondiente.');
  }

  console.log('Formato asignado: ' + formato.nombre);

  let libroMensual = null;
  let libroFormato = null;

  try {
    libroMensual = abrirArchivoComoHoja_(mensual);
    libroFormato = abrirArchivoComoHoja_(formato);

    const productos = extraerProductosActualizados_(libroMensual.id);

    if (productos.size === 0) {
      throw new Error(
        'No se encontraron productos en Pedido Diario o Bodega.'
      );
    }

    const categorias = obtenerCategoriasPorCodigo_(
      libroFormato.id,
      productos
    );

    const nombresCategorias = new Set();
    categorias.forEach(lista => {
      lista.forEach(categoria => nombresCategorias.add(categoria));
    });

    if (nombresCategorias.size === 0) {
      throw new Error(
        'No se detectó ninguna categoría dentro de la hoja Mensual.'
      );
    }

    console.log(
      'Categorías detectadas: ' +
      Array.from(nombresCategorias).sort().join(' | ')
    );

    const filas = construirFilasSalida_(productos, categorias);
    const nombreSalida = crearNombreSalida_(mensual.nombre);

    generarExcel_(nombreSalida, filas, carpetaSalida);

  } finally {
    cerrarTemporal_(libroMensual);
    cerrarTemporal_(libroFormato);
  }
}

function extraerProductosActualizados_(spreadsheetId) {
  const libro = SpreadsheetApp.openById(spreadsheetId);
  const productos = new Map();

  CONFIG.HOJAS_FUENTE.forEach(nombreHoja => {
    const hoja = buscarHoja_(libro, nombreHoja);

    if (!hoja) {
      console.log('No se encontró la hoja: ' + nombreHoja);
      return;
    }

    const estructura = detectarColumnas_(hoja);

    if (!estructura) {
      console.log(
        'No se detectaron columnas en la hoja: ' + hoja.getName()
      );
      return;
    }

    const ultimaFila = hoja.getLastRow();

    if (ultimaFila <= estructura.filaEncabezado) return;

    const columnasNecesarias = [
      estructura.colCodigo,
      estructura.colProducto
    ];

    if (estructura.colUnidad !== null) {
      columnasNecesarias.push(estructura.colUnidad);
    }

    const primeraColumna = Math.min.apply(null, columnasNecesarias);
    const ultimaColumna = Math.max.apply(null, columnasNecesarias);
    const cantidadFilas = ultimaFila - estructura.filaEncabezado;

    const valores = hoja.getRange(
      estructura.filaEncabezado + 1,
      primeraColumna + 1,
      cantidadFilas,
      ultimaColumna - primeraColumna + 1
    ).getDisplayValues();

    valores.forEach(fila => {
      const codigo = normalizarCodigo_(
        fila[estructura.colCodigo - primeraColumna]
      );

      let productoOriginal = String(
        fila[estructura.colProducto - primeraColumna] || ''
      ).trim();

      if (!codigo || !productoOriginal) return;

      const separado = separarUnidadEmpaque_(productoOriginal);
      // El producto se conserva completo, exactamente como está en el archivo 09.
      // La presentación solo se copia a la columna U.D MED.
      const producto = productoOriginal;
      const unidad = separado.unidad;

      if (!productos.has(codigo)) {
        productos.set(codigo, {
          codigo: codigo,
          producto: producto,
          unidad: normalizarUnidad_(unidad)
        });

      } else {
        const existente = productos.get(codigo);

        if (!existente.producto && producto) existente.producto = producto;
        if (!existente.unidad && unidad) {
          existente.unidad = normalizarUnidad_(unidad);
        }
      }
    });
  });

  return productos;
}

/**
 * Busca cada código dentro de la hoja Mensual del formato.
 * La categoría se toma del título de sección más cercano que aparezca
 * encima del código, por ejemplo: Bebidas, Plancha, Cocina o Bodega.
 */
function obtenerCategoriasPorCodigo_(spreadsheetId, productos) {
  const libro = SpreadsheetApp.openById(spreadsheetId);
  const categorias = new Map();

  productos.forEach((_, codigo) => categorias.set(codigo, new Set()));

  const hojasMensuales = libro.getSheets().filter(hoja => {
    const nombre = normalizarTexto_(hoja.getName());

    return CONFIG.HOJAS_CATEGORIAS.some(nombreConfigurado => {
      const buscado = normalizarTexto_(nombreConfigurado);
      return nombre === buscado || nombre.includes(buscado);
    });
  });

  if (hojasMensuales.length === 0) {
    throw new Error(
      'El formato no contiene la hoja Mensual o Formato de Inventario Mensual.'
    );
  }

  hojasMensuales.forEach(hoja => {
    const filas = Math.min(hoja.getLastRow(), 5000);
    const columnas = Math.min(hoja.getLastColumn(), 40);

    if (filas === 0 || columnas === 0) return;

    const valores = hoja
      .getRange(1, 1, filas, columnas)
      .getDisplayValues();

    const tablaCategorias = detectarTablaCategorias_(valores);

    if (tablaCategorias) {
      asignarCategoriasDesdeTabla_(
        valores,
        tablaCategorias,
        productos,
        categorias
      );
    }

    const anclas = detectarAnclasCategorias_(hoja, valores, productos);

    valores.forEach((fila, indiceFila) => {
      fila.forEach((valor, indiceColumna) => {
        codigosPosiblesEnCelda_(valor).forEach(codigo => {
          if (productos.has(codigo)) {
            const categoria = categoriaParaCelda_(
              anclas,
              indiceFila + 1,
              indiceColumna + 1
            ) || categoriaEnMismaFila_(
              fila,
              indiceColumna,
              productos,
              anclas,
              indiceFila + 1
            );

            if (categoria) {
              categorias.get(codigo).add(categoria);
            }
          }
        });
      });
    });
  });

  return categorias;
}

function detectarTablaCategorias_(valores) {
  const limite = Math.min(valores.length, 100);

  for (let fila = 0; fila < limite; fila++) {
    let colItem = null;
    let colCategoria = null;

    valores[fila].forEach((valor, columna) => {
      const texto = normalizarTexto_(valor);

      if (esEncabezadoCodigo_(texto)) colItem = columna;

      if (
        texto === 'CATEGORIA' ||
        texto === 'SECCION' ||
        texto === 'AREA' ||
        texto === 'UBICACION' ||
        texto === 'CATEGORIA INVENTARIO'
      ) {
        colCategoria = columna;
      }
    });

    if (colItem !== null && colCategoria !== null) {
      return {
        filaEncabezado: fila,
        colItem: colItem,
        colCategoria: colCategoria
      };
    }
  }

  return null;
}

function asignarCategoriasDesdeTabla_(
  valores,
  estructura,
  productos,
  categorias
) {
  let categoriaActual = '';

  for (
    let fila = estructura.filaEncabezado + 1;
    fila < valores.length;
    fila++
  ) {
    const categoriaCelda = String(
      valores[fila][estructura.colCategoria] || ''
    ).trim();

    if (esCategoriaCandidata_(categoriaCelda, productos)) {
      categoriaActual = limpiarCategoria_(categoriaCelda);
    }

    const codigo = normalizarCodigo_(
      valores[fila][estructura.colItem]
    );

    if (
      codigo &&
      productos.has(codigo) &&
      categoriaActual
    ) {
      categorias.get(codigo).add(categoriaActual);
    }
  }
}

function detectarAnclasCategorias_(hoja, valores, productos) {
  const anclas = [];
  const claves = new Set();

  // Los títulos de sección normalmente están en celdas combinadas.
  hoja.getDataRange().getMergedRanges().forEach(rango => {
    const texto = String(rango.getDisplayValue() || '').trim();

    if (!esCategoriaCandidata_(texto, productos)) return;

    agregarAnclaCategoria_(anclas, claves, {
      categoria: limpiarCategoria_(texto),
      fila: rango.getRow(),
      columnaInicio: rango.getColumn(),
      columnaFin: rango.getLastColumn(),
      prioridad: 10
    });
  });

  // También detecta encabezados de sección no combinados.
  valores.forEach((fila, indiceFila) => {
    const celdasConTexto = [];
    let contieneCodigoProducto = false;

    fila.forEach((valor, indiceColumna) => {
      const texto = String(valor || '').trim();
      if (!texto) return;

      celdasConTexto.push({
        texto: texto,
        columna: indiceColumna + 1
      });

      codigosPosiblesEnCelda_(texto).forEach(codigo => {
        if (productos.has(codigo)) contieneCodigoProducto = true;
      });
    });

    if (contieneCodigoProducto || celdasConTexto.length === 0) return;

    celdasConTexto.forEach(celda => {
      if (!esCategoriaCandidata_(celda.texto, productos)) return;

      const textoOriginal = celda.texto.trim();
      const pocasCeldas = celdasConTexto.length <= 3;
      const pareceTitulo =
        textoOriginal === textoOriginal.toUpperCase() || pocasCeldas;

      if (!pareceTitulo) return;

      agregarAnclaCategoria_(anclas, claves, {
        categoria: limpiarCategoria_(textoOriginal),
        fila: indiceFila + 1,
        columnaInicio: Math.max(1, celda.columna - 2),
        columnaFin: Math.min(fila.length, celda.columna + 4),
        prioridad: pocasCeldas ? 6 : 4
      });
    });
  });

  return anclas;
}

function agregarAnclaCategoria_(anclas, claves, ancla) {
  const clave = [
    normalizarTexto_(ancla.categoria),
    ancla.fila,
    ancla.columnaInicio,
    ancla.columnaFin
  ].join('|');

  if (claves.has(clave)) return;
  claves.add(clave);
  anclas.push(ancla);
}

function categoriaParaCelda_(anclas, filaCodigo, columnaCodigo) {
  let mejor = null;
  let mejorPuntaje = -Infinity;

  anclas.forEach(ancla => {
    if (ancla.fila > filaCodigo) return;

    const distanciaFilas = filaCodigo - ancla.fila;
    if (distanciaFilas > 150) return;

    let distanciaColumnas = 0;

    if (columnaCodigo < ancla.columnaInicio) {
      distanciaColumnas = ancla.columnaInicio - columnaCodigo;
    } else if (columnaCodigo > ancla.columnaFin) {
      distanciaColumnas = columnaCodigo - ancla.columnaFin;
    }

    if (distanciaColumnas > 5) return;

    const puntaje =
      ancla.prioridad -
      distanciaFilas * 0.08 -
      distanciaColumnas * 1.5;

    if (puntaje > mejorPuntaje) {
      mejorPuntaje = puntaje;
      mejor = ancla;
    }
  });

  return mejor ? mejor.categoria : '';
}

function categoriaEnMismaFila_(
  fila,
  columnaCodigo,
  productos,
  anclas,
  numeroFila
) {
  // Primero utiliza un título detectado exactamente en la misma fila.
  const anclasMismaFila = anclas
    .filter(ancla => ancla.fila === numeroFila)
    .sort((a, b) => {
      const distanciaA = distanciaAColumna_(a, columnaCodigo + 1);
      const distanciaB = distanciaAColumna_(b, columnaCodigo + 1);
      return distanciaA - distanciaB;
    });

  if (anclasMismaFila.length > 0) {
    return anclasMismaFila[0].categoria;
  }

  // Como respaldo, busca una celda corta de categoría en la misma fila.
  // Se revisan primero las columnas situadas a la izquierda del ítem.
  const orden = [];

  for (let col = columnaCodigo - 1; col >= 0; col--) orden.push(col);
  for (let col = columnaCodigo + 1; col < fila.length; col++) orden.push(col);

  for (let i = 0; i < orden.length; i++) {
    const texto = String(fila[orden[i]] || '').trim();

    if (!esCategoriaCandidata_(texto, productos)) continue;

    const normalizado = normalizarTexto_(texto);
    const palabras = normalizado.split(' ').filter(Boolean);

    if (
      texto === texto.toUpperCase() &&
      palabras.length <= 4
    ) {
      return limpiarCategoria_(texto);
    }
  }

  return '';
}

function distanciaAColumna_(ancla, columna) {
  if (columna < ancla.columnaInicio) {
    return ancla.columnaInicio - columna;
  }

  if (columna > ancla.columnaFin) {
    return columna - ancla.columnaFin;
  }

  return 0;
}

function esCategoriaCandidata_(valor, productos) {
  const textoOriginal = String(valor || '').trim();
  const texto = normalizarTexto_(textoOriginal);

  if (!texto || texto.length < 3 || texto.length > 55) return false;
  if (/^\d+(?:[.,]\d+)?$/.test(textoOriginal)) return false;

  const palabrasProhibidas = [
    'FORMATO',
    'INVENTARIO',
    'PUNTO DE VENTA',
    'FECHA',
    'RESPONSABLE',
    'FIRMA',
    'OBSERVACION',
    'CODIGO',
    'PRODUCTO',
    'DESCRIPCION',
    'UNIDAD',
    'CANTIDAD',
    'CONTEO',
    'ABIERTO',
    'CERRADO',
    'TOTAL',
    'MENSUAL'
  ];

  if (palabrasProhibidas.some(palabra => texto.includes(palabra))) {
    return false;
  }

  let coincideConCodigo = false;

  codigosPosiblesEnCelda_(textoOriginal).forEach(codigo => {
    if (productos.has(codigo)) coincideConCodigo = true;
  });

  if (coincideConCodigo) return false;

  const numeroPalabras = texto.split(' ').filter(Boolean).length;
  return numeroPalabras <= 6;
}

function limpiarCategoria_(categoria) {
  return String(categoria || '')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/^[-–—:]+|[-–—:]+$/g, '')
    .trim();
}

function construirFilasSalida_(productos, categorias) {
  const filas = [];

  productos.forEach(producto => {
    const categoriasProducto = categorias.get(producto.codigo);

    if (!categoriasProducto || categoriasProducto.size === 0) {
      filas.push([
        producto.codigo,
        producto.producto,
        producto.unidad,
        'SIN CATEGORÍA'
      ]);

      return;
    }

    Array.from(categoriasProducto).forEach(categoria => {
      filas.push([
        producto.codigo,
        producto.producto,
        producto.unidad,
        categoria
      ]);
    });
  });

  filas.sort((a, b) => {
    const porCategoria = a[3].localeCompare(b[3], 'es');
    if (porCategoria !== 0) return porCategoria;
    return a[1].localeCompare(b[1], 'es');
  });

  return filas;
}

function generarExcel_(nombreArchivo, filas, carpetaSalida) {
  const temporal = SpreadsheetApp.create(
    'TEMPORAL_SALIDA_' + Date.now()
  );

  try {
    const hoja = temporal.getSheets()[0];
    hoja.setName('BASE');

    const encabezados = [[
      'ÍTEM',
      'PRODUCTO',
      'U.D MED',
      'CATEGORÍA'
    ]];

    hoja.getRange(1, 1, 1, 4).setValues(encabezados);

    if (filas.length > 0) {
      hoja.getRange(2, 1, filas.length, 4).setValues(filas);
      hoja.getRange(2, 1, filas.length, 1).setNumberFormat('@');
    }

    hoja.setFrozenRows(1);
    hoja.setColumnWidth(1, 110);
    hoja.setColumnWidth(2, 390);
    hoja.setColumnWidth(3, 180);
    hoja.setColumnWidth(4, 190);

    hoja.getRange(1, 1, 1, 4)
      .setBackground(CONFIG.COLOR_CAFE)
      .setFontColor('#FFFFFF')
      .setFontWeight('bold')
      .setHorizontalAlignment('center');

    if (filas.length > 0) {
      hoja.getRange(2, 1, filas.length, 4)
        .setVerticalAlignment('middle');

      hoja.getRange(1, 1, filas.length + 1, 4).createFilter();
      aplicarFilasAlternas_(hoja, filas.length);
    }

    SpreadsheetApp.flush();
    Utilities.sleep(1200);

    const blob = exportarComoXlsx_(temporal.getId(), nombreArchivo);
    carpetaSalida.createFile(blob);

  } finally {
    DriveApp.getFileById(temporal.getId()).setTrashed(true);
  }
}

function exportarComoXlsx_(spreadsheetId, nombreArchivo) {
  const url =
    'https://docs.google.com/spreadsheets/d/' + spreadsheetId +
    '/export?format=xlsx';

  const respuesta = UrlFetchApp.fetch(url, {
    headers: {
      Authorization: 'Bearer ' + ScriptApp.getOAuthToken()
    },
    muteHttpExceptions: true
  });

  if (respuesta.getResponseCode() !== 200) {
    throw new Error(
      'No fue posible exportar el Excel. Código HTTP: ' +
      respuesta.getResponseCode()
    );
  }

  return respuesta.getBlob().setName(nombreArchivo);
}

function crearZipFinal_(carpetaSalida) {
  const archivos = carpetaSalida.getFiles();
  const blobs = [];

  while (archivos.hasNext()) {
    const archivo = archivos.next();

    if (/\.xlsx$/i.test(archivo.getName())) {
      blobs.push(archivo.getBlob().setName(archivo.getName()));
    }
  }

  if (blobs.length === 0) {
    throw new Error('No se generaron archivos para incluir en el ZIP.');
  }

  const nombreZip = 'INVENTARIOS_PDV_GENERADOS.zip';
  const existentes = carpetaSalida.getFilesByName(nombreZip);

  while (existentes.hasNext()) {
    existentes.next().setTrashed(true);
  }

  return carpetaSalida.createFile(
    Utilities.zip(blobs, nombreZip)
  );
}

function detectarColumnas_(hoja) {
  const filas = Math.min(hoja.getLastRow(), 60);
  const columnas = Math.min(hoja.getLastColumn(), 40);

  if (filas === 0 || columnas === 0) return null;

  const valores = hoja
    .getRange(1, 1, filas, columnas)
    .getDisplayValues();

  let mejor = null;

  valores.forEach((fila, indiceFila) => {
    let colCodigo = null;
    let colProducto = null;
    let colUnidad = null;

    fila.forEach((valor, indiceColumna) => {
      const texto = normalizarTexto_(valor);

      if (esEncabezadoCodigo_(texto)) colCodigo = indiceColumna;
      if (esEncabezadoProducto_(texto)) colProducto = indiceColumna;
      if (esEncabezadoUnidad_(texto)) colUnidad = indiceColumna;
    });

    let puntaje = 0;
    if (colCodigo !== null) puntaje += 3;
    if (colProducto !== null) puntaje += 3;
    if (colUnidad !== null) puntaje += 1;

    if (
      colCodigo !== null &&
      colProducto !== null &&
      (!mejor || puntaje > mejor.puntaje)
    ) {
      mejor = {
        filaEncabezado: indiceFila + 1,
        colCodigo: colCodigo,
        colProducto: colProducto,
        colUnidad: colUnidad,
        puntaje: puntaje
      };
    }
  });

  return mejor;
}

function separarUnidadEmpaque_(nombreProducto) {
  const texto = String(nombreProducto || '').trim();

  const expresion = /\s*(?:[-–—]\s*)?(X\s*\d+(?:[.,]\d+)?\s*(?:ML|MILILITROS?|L|LT|LTS|LITROS?|G|GR|GRS|GRAMOS?|KG|KILOS?|UND|UNDS|UNID|UNIDS|UNIDADES?|U|OZ|LB|LIBRAS?|CC|PAQ(?:UETE)?S?|BOLSAS?|BOTELLAS?|LATAS?|CAJAS?|CUBETAS?)?)\s*[;,.]?\s*$/i;

  const coincidencia = texto.match(expresion);

  if (!coincidencia) {
    return {
      producto: texto,
      unidad: ''
    };
  }

  return {
    producto: texto.replace(expresion, '').trim(),
    unidad: coincidencia[1]
      .replace(/\s+/g, ' ')
      .toUpperCase()
  };
}

function normalizarUnidad_(unidad) {
  return String(unidad || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toUpperCase();
}

function normalizarCodigo_(valor) {
  let codigo = String(valor == null ? '' : valor).trim();

  codigo = codigo
    .replace(/^'/, '')
    .replace(/\s+/g, '')
    .replace(/\.0+$/, '')
    .toUpperCase();

  if (!codigo) return '';
  if (/^(TOTAL|CODIGO|CÓDIGO|ITEM|REFERENCIA)$/i.test(codigo)) return '';

  return codigo;
}

function codigosPosiblesEnCelda_(valor) {
  const texto = String(valor == null ? '' : valor).trim();
  const resultado = new Set();

  const exacto = normalizarCodigo_(texto);
  if (exacto) resultado.add(exacto);

  const encontrados = texto.toUpperCase().match(/\b[A-Z]{0,3}\d{3,10}\b/g) || [];

  encontrados.forEach(codigo => {
    const limpio = normalizarCodigo_(codigo);
    if (limpio) resultado.add(limpio);
  });

  return Array.from(resultado);
}

function buscarMejorFormato_(nombreMensual, formatos) {
  let mejor = null;
  let mejorPuntaje = -Infinity;

  formatos.forEach(formato => {
    const puntaje = puntajeCoincidencia_(nombreMensual, formato.nombre);

    if (puntaje > mejorPuntaje) {
      mejorPuntaje = puntaje;
      mejor = formato;
    }
  });

  console.log(
    'Coincidencia de formato para ' + nombreMensual +
    ': ' + (mejor ? mejor.nombre : 'ninguno') +
    ' — puntaje ' + mejorPuntaje.toFixed(2)
  );

  return mejorPuntaje >= 0.45 ? mejor : null;
}

function puntajeCoincidencia_(mensual, formato) {
  const claveMensual = claveNombre_(mensual);
  const claveFormato = claveNombre_(formato);

  let puntaje = 0;

  if (claveMensual === claveFormato) {
    puntaje += 2;
  } else if (
    claveMensual.includes(claveFormato) ||
    claveFormato.includes(claveMensual)
  ) {
    puntaje += 0.8;
  }

  const tokensMensual = new Set(claveMensual.split(' ').filter(Boolean));
  const tokensFormato = new Set(claveFormato.split(' ').filter(Boolean));
  const union = new Set([...tokensMensual, ...tokensFormato]);
  let comunes = 0;

  tokensMensual.forEach(token => {
    if (tokensFormato.has(token)) comunes++;
  });

  if (union.size > 0) puntaje += comunes / union.size;

  const tipoMensual = tipoPdv_(mensual);
  const tipoFormato = tipoPdv_(formato);

  if (tipoMensual === tipoFormato) {
    puntaje += 0.35;
  } else {
    puntaje -= 0.35;
  }

  return puntaje;
}

function claveNombre_(nombre) {
  let texto = normalizarTexto_(nombre)
    .replace(/\.(XLSX|XLS|XLSM)$/g, ' ')
    .replace(/\(\d+\)$/g, ' ')
    .replace(/\b09\b/g, ' ')
    .replace(/^B[RHCD]?\s*\d+\s*[-.]?\s*/g, ' ')
    .replace(/^H\s*\d+\s*/g, ' ')
    .replace(/\bHELADERIA\b/g, ' ')
    .replace(/\bRESTAURANTE\b/g, ' ')
    .replace(/^H\b/g, ' ')
    .replace(/\bETAPA\b/g, ' ')
    .replace(/\bTOGO\b/g, 'TO GO')
    .replace(/[^A-Z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return texto.toLowerCase();
}

function tipoPdv_(nombre) {
  const texto = normalizarTexto_(nombre);

  if (/^BH\s*\d+/.test(texto) || /^H(?:\.|\s|\d)/.test(texto)) {
    return 'HELADERIA';
  }

  if (/^BC\s*\d+/.test(texto) || /\bCOCINA\b/.test(texto)) {
    return 'COCINA';
  }

  return 'RESTAURANTE';
}

function listarArchivos_(carpeta) {
  const archivos = carpeta.getFiles();
  const resultado = [];

  while (archivos.hasNext()) {
    const archivo = archivos.next();
    const nombre = archivo.getName();

    if (!/\.(xlsx|xls|xlsm)$/i.test(nombre) &&
        archivo.getMimeType() !== MimeType.GOOGLE_SHEETS) {
      continue;
    }

    resultado.push({
      id: archivo.getId(),
      nombre: nombre,
      mimeType: archivo.getMimeType(),
      actualizado: archivo.getLastUpdated().getTime()
    });
  }

  resultado.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  return resultado;
}

function quitarDuplicadosFormatos_(archivos) {
  const porNombre = new Map();

  archivos.forEach(archivo => {
    const clave = normalizarTexto_(archivo.nombre)
      .replace(/\.(XLSX|XLS|XLSM)$/g, '')
      .replace(/\(\d+\)$/g, '')
      .trim();

    if (
      !porNombre.has(clave) ||
      archivo.actualizado > porNombre.get(clave).actualizado
    ) {
      porNombre.set(clave, archivo);
    }
  });

  return Array.from(porNombre.values());
}

function abrirArchivoComoHoja_(archivo) {
  if (archivo.mimeType === MimeType.GOOGLE_SHEETS) {
    return {
      id: archivo.id,
      temporal: false
    };
  }

  const original = DriveApp.getFileById(archivo.id);

  const convertido = Drive.Files.create(
    {
      name: 'TEMPORAL_' + Date.now() + '_' + archivo.nombre,
      mimeType: MimeType.GOOGLE_SHEETS
    },
    original.getBlob(),
    {
      fields: 'id,name'
    }
  );

  return {
    id: convertido.id,
    temporal: true
  };
}

function cerrarTemporal_(libro) {
  if (!libro || !libro.temporal || !libro.id) return;

  try {
    DriveApp.getFileById(libro.id).setTrashed(true);
  } catch (error) {
    console.log('No se pudo borrar un archivo temporal: ' + error.message);
  }
}

function buscarHoja_(libro, nombre) {
  const buscado = normalizarTexto_(nombre);

  return libro.getSheets().find(hoja =>
    normalizarTexto_(hoja.getName()) === buscado
  ) || null;
}

function esEncabezadoCodigo_(texto) {
  return (
    texto === 'CODIGO' ||
    texto === 'COD' ||
    texto === 'ITEM' ||
    texto === 'CODIGO ITEM' ||
    texto === 'REFERENCIA' ||
    texto.includes('CODIGO DEL PRODUCTO')
  );
}

function esEncabezadoProducto_(texto) {
  return (
    texto === 'PRODUCTO' ||
    texto === 'DESCRIPCION' ||
    texto === 'NOMBRE PRODUCTO' ||
    texto === 'NOMBRE DEL PRODUCTO' ||
    texto === 'DESCRIPCION PRODUCTO' ||
    texto === 'DESCRIPCION DEL PRODUCTO' ||
    texto === 'DESCRIPCION ITEM' ||
    texto === 'ARTICULO'
  );
}

function esEncabezadoUnidad_(texto) {
  return (
    texto === 'UNIDAD' ||
    texto === 'UM' ||
    texto === 'U M' ||
    texto === 'DESC UM' ||
    texto === 'UNIDAD DE MEDIDA' ||
    texto === 'UNIDAD DE EMPAQUE' ||
    texto === 'PRESENTACION' ||
    texto.includes('DESC U M')
  );
}

function normalizarTexto_(valor) {
  return String(valor == null ? '' : valor)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function crearNombreSalida_(nombreMensual) {
  const base = nombreMensual
    .replace(/\.xlsx$/i, '')
    .replace(/\s*09\s*$/i, '')
    .trim();

  return limpiarNombreArchivo_(base + ' - BASE INVENTARIO.xlsx');
}

function limpiarNombreArchivo_(nombre) {
  return nombre.replace(/[\\/:*?"<>|]/g, '-');
}

function aplicarFilasAlternas_(hoja, cantidadFilas) {
  for (let fila = 2; fila <= cantidadFilas + 1; fila++) {
    if (fila % 2 === 0) {
      hoja.getRange(fila, 1, 1, 4).setBackground(CONFIG.COLOR_CREMA);
    }
  }
}

function eliminarTriggersContinuacion_() {
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === 'continuarGeneracion') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

/**
 * Ejecutar para consultar el avance y obtener el enlace del ZIP.
 */
function verEstado() {
  const propiedades = PropertiesService.getScriptProperties();
  const estado = propiedades.getProperty('ESTADO') || 'NO INICIADO';
  const indice = propiedades.getProperty('INDICE') || '0';
  const total = propiedades.getProperty('TOTAL') || '0';
  const carpetaId = propiedades.getProperty('CARPETA_SALIDA_ID');
  const zipUrl = propiedades.getProperty('ZIP_URL');
  const errores = JSON.parse(propiedades.getProperty('ERRORES') || '[]');

  console.log('ESTADO: ' + estado);
  console.log('AVANCE: ' + indice + ' de ' + total);

  if (carpetaId) {
    console.log(
      'CARPETA DE RESULTADOS: ' +
      DriveApp.getFolderById(carpetaId).getUrl()
    );
  }

  if (zipUrl) console.log('ZIP FINAL: ' + zipUrl);

  if (errores.length > 0) {
    console.log('NOVEDADES:');
    errores.forEach(error => console.log(error));
  }
}

/**
 * Solo usar si deseas cancelar el estado guardado y comenzar de nuevo.
 * No borra las carpetas de resultados ya creadas.
 */
function reiniciarEstado() {
  eliminarTriggersContinuacion_();
  PropertiesService.getScriptProperties().deleteAllProperties();
  console.log('Estado reiniciado. Ya puedes ejecutar iniciarGeneracion.');
}
