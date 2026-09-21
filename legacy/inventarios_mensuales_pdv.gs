const ID_CARPETA_MENSUAL =
  '1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk';

const NOMBRE_CARPETA_BASES =
  'Bases Google - Inventarios Mensuales';

const CANTIDAD_POR_EJECUCION = 5;

// La caché evita buscar y abrir repetidamente los mismos archivos de Drive.
// Esto reduce especialmente el tiempo de carga y de guardado en la página.
const CACHE_PDV_SEGUNDOS = 600;
const CACHE_ARCHIVO_SEGUNDOS = 21600;
const CACHE_PRODUCTOS_SEGUNDOS = 600;
const DIAS_RETENCION_CONTEOS_MENSUALES = 5;
const HORA_LIMPIEZA_AUTOMATICA = 2;

// Reemplace el texto por su correo corporativo.
// Puede agregar más correos, separados por coma.
const CORREOS_ADMIN = [
  'info.costos@crepesywafflesantioquia.com'
];


function prepararBasesMensuales() {
  const carpetaOrigen =
    DriveApp.getFolderById(ID_CARPETA_MENSUAL);

  const carpetaBases =
    obtenerOCrearCarpetaBases_(carpetaOrigen);

  const archivos = carpetaOrigen.getFiles();

  let totalExcel = 0;
  let convertidos = 0;
  let pendientes = 0;
  let procesadosAhora = 0;
  const errores = [];

  while (archivos.hasNext()) {
    const archivo = archivos.next();
    const nombreArchivo = archivo.getName();

    if (!nombreArchivo.toLowerCase().endsWith('.xlsx')) {
      continue;
    }

    totalExcel++;

    const nombreBase = nombreArchivo
      .replace(/\.xlsx$/i, '')
      .trim();

    const existentes =
      carpetaBases.getFilesByName(nombreBase);

    if (existeHojaGoogle_(existentes)) {
      convertidos++;
      continue;
    }

    if (procesadosAhora >= CANTIDAD_POR_EJECUCION) {
      pendientes++;
      continue;
    }

    try {
      const archivoConvertido = Drive.Files.create(
        {
          name: nombreBase,
          mimeType:
            'application/vnd.google-apps.spreadsheet',
          parents: [carpetaBases.getId()]
        },
        archivo.getBlob(),
        {
          fields: 'id,name,mimeType'
        }
      );

      const libro =
        SpreadsheetApp.openById(archivoConvertido.id);

      const hojaMensual =
        buscarHoja_(libro, 'Mensual');

      if (!hojaMensual) {
        DriveApp
          .getFileById(archivoConvertido.id)
          .setTrashed(true);

        throw new Error(
          'El archivo no contiene la hoja Mensual.'
        );
      }

      convertidos++;
      procesadosAhora++;

      CacheService
        .getScriptCache()
        .remove('mensual:pdv:listado');

    } catch (error) {
      errores.push(
        nombreArchivo + ': ' + error.message
      );
    }
  }

  const estado =
    convertidos === totalExcel
      ? 'COMPLETADO'
      : 'PENDIENTE DE CONTINUAR';

  console.log('ESTADO: ' + estado);
  console.log(
    'AVANCE: ' + convertidos + ' de ' + totalExcel
  );
  console.log(
    'PROCESADOS EN ESTA EJECUCIÓN: ' +
    procesadosAhora
  );
  console.log(
    'CARPETA DE BASES: ' +
    carpetaBases.getUrl()
  );

  if (errores.length > 0) {
    console.log(
      'ERRORES: ' + errores.join(' | ')
    );
  }

  return {
    estado: estado,
    convertidos: convertidos,
    total: totalExcel,
    procesadosAhora: procesadosAhora,
    pendientes: Math.max(
      totalExcel - convertidos,
      pendientes
    ),
    carpeta: carpetaBases.getUrl(),
    errores: errores
  };
}


function obtenerOCrearCarpetaBases_(carpetaOrigen) {
  const carpetas =
    carpetaOrigen.getFoldersByName(
      NOMBRE_CARPETA_BASES
    );

  if (carpetas.hasNext()) {
    return carpetas.next();
  }

  return carpetaOrigen.createFolder(
    NOMBRE_CARPETA_BASES
  );
}


function existeHojaGoogle_(archivos) {
  while (archivos.hasNext()) {
    const archivo = archivos.next();

    if (
      archivo.getMimeType() ===
      'application/vnd.google-apps.spreadsheet'
    ) {
      return true;
    }
  }

  return false;
}


function buscarHoja_(libro, nombreBuscado) {
  const nombreNormalizado =
    normalizar_(nombreBuscado);

  return libro.getSheets().find(hoja =>
    normalizar_(hoja.getName()) ===
    nombreNormalizado
  ) || null;
}


function normalizar_(texto) {
  return String(texto || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}
/* =====================================================
   PÁGINA WEB - INVENTARIOS MENSUALES
   ===================================================== */


function doGet() {
  return HtmlService
    .createHtmlOutputFromFile('Index')
    .setTitle('Inventarios Mensuales PDV')
    .addMetaTag(
      'viewport',
      'width=device-width, initial-scale=1'
    );
}


function obtenerEstadoAdministrador() {
  const correo = obtenerCorreoUsuario_();

  return {
    esAdministrador:
      esCorreoAdministrador_(correo)
  };
}


function obtenerCorreoUsuario_() {
  return String(
    Session.getActiveUser().getEmail() || ''
  )
    .trim()
    .toLowerCase();
}


function esCorreoAdministrador_(correo) {
  const correosPermitidos =
    CORREOS_ADMIN
      .map(valor =>
        String(valor || '')
          .trim()
          .toLowerCase()
      )
      .filter(valor =>
        valor !== '' &&
        valor !== 'escribe_aqui_tu_correo'
      );

  return correo !== '' &&
    correosPermitidos.includes(correo);
}


function validarAccesoAdministrador_() {
  const correo = obtenerCorreoUsuario_();

  if (!esCorreoAdministrador_(correo)) {
    throw new Error(
      'No tiene autorización para acceder ' +
      'a la administración ni descargar archivos.'
    );
  }
}


function obtenerCarpetaBasesMensuales_() {
  const carpetaOrigen =
    DriveApp.getFolderById(ID_CARPETA_MENSUAL);

  return obtenerOCrearCarpetaBases_(
    carpetaOrigen
  );
}


function obtenerPuntosVenta() {
  const cache =
    CacheService.getScriptCache();

  const puntosEnCache =
    cache.get('mensual:pdv:listado');

  if (puntosEnCache) {
    try {
      return JSON.parse(puntosEnCache);
    } catch (error) {
      cache.remove('mensual:pdv:listado');
    }
  }

  const carpeta =
    obtenerCarpetaBasesMensuales_();

  const archivos = carpeta.getFiles();
  const puntosVenta = [];

  while (archivos.hasNext()) {
    const archivo = archivos.next();

    if (
      archivo.getMimeType() ===
      'application/vnd.google-apps.spreadsheet'
    ) {
      puntosVenta.push(
        archivo.getName().trim()
      );
    }
  }

  const resultado = puntosVenta
    .filter((nombre, posicion, lista) =>
      lista.indexOf(nombre) === posicion
    )
    .sort((a, b) =>
      a.localeCompare(b, 'es')
    );

  cache.put(
    'mensual:pdv:listado',
    JSON.stringify(resultado),
    CACHE_PDV_SEGUNDOS
  );

  return resultado;
}


function obtenerCategorias(puntoVenta) {
  const productos =
    obtenerProductos(puntoVenta);

  return [...new Set(
    productos
      .map(producto => producto.categoria)
      .filter(categoria => categoria !== '')
  )].sort((a, b) =>
    a.localeCompare(b, 'es')
  );
}


function obtenerProductos(
  puntoVenta,
  categoriaSeleccionada
) {
  const cache =
    CacheService.getScriptCache();

  const claveCache =
    crearClaveCacheMensual_(
      'productos',
      puntoVenta
    );

  let productos = null;
  const productosEnCache =
    cache.get(claveCache);

  if (productosEnCache) {
    try {
      productos = JSON.parse(
        productosEnCache
      );
    } catch (error) {
      cache.remove(claveCache);
    }
  }

  if (!productos) {
    const libro =
      obtenerLibroMensualPDV_(puntoVenta);

    const hoja =
      buscarHoja_(libro, 'Mensual');

    if (!hoja) {
      throw new Error(
        'No se encontró la hoja Mensual para ' +
        puntoVenta + '.'
      );
    }

    const ultimaFila = hoja.getLastRow();
    const ultimaColumna =
      hoja.getLastColumn();

    if (
      ultimaFila < 2 ||
      ultimaColumna < 3
    ) {
      return [];
    }

    const datos = hoja
      .getRange(
        1,
        1,
        ultimaFila,
        ultimaColumna
      )
      .getDisplayValues();

    const encabezados =
      datos[0].map(normalizar_);

    let columnaCategoria =
      buscarIndiceMensual_(
        encabezados,
        ['categoria']
      );

    let columnaItem =
      buscarIndiceMensual_(
        encabezados,
        [
          'item',
          'codigo',
          'cod',
          'id producto'
        ]
      );

    let columnaProducto =
      buscarIndiceMensual_(
        encabezados,
        [
          'nombre producto',
          'producto',
          'descripcion',
          'desc item'
        ]
      );

    let columnaUDM =
      buscarIndiceMensual_(
        encabezados,
        [
          'desc u m',
          'desc um',
          'descripcion unidad de medida',
          'udm',
          'unidad de medida',
          'unidad',
          'um empaque'
        ]
      );

    if (columnaCategoria === -1) {
      columnaCategoria = 0;
    }

    if (columnaItem === -1) {
      columnaItem = 1;
    }

    if (columnaProducto === -1) {
      columnaProducto = 2;
    }

    if (columnaUDM === -1) {
      columnaUDM = 3;
    }

    productos = datos
      .slice(1)
      .map((fila, posicion) => ({
      id: posicion + 1,

      categoria:
        limpiarTextoMensual_(
          fila[columnaCategoria]
        ),

      item:
        limpiarTextoMensual_(
          fila[columnaItem]
        ),

      producto:
        limpiarTextoMensual_(
          fila[columnaProducto]
        ),

      udm:
        limpiarTextoMensual_(
          fila[columnaUDM]
        )
      }))
      .filter(producto =>
        producto.categoria !== '' &&
        producto.item !== '' &&
        producto.producto !== '' &&
        normalizar_(producto.producto) !==
          'no tiene'
      );

    // Apps Script limita el tamaño de cada valor en caché.
    // Si la lista es demasiado grande, simplemente se omite sin fallar.
    try {
      cache.put(
        claveCache,
        JSON.stringify(productos),
        CACHE_PRODUCTOS_SEGUNDOS
      );
    } catch (error) {
      console.log(
        'No fue posible almacenar productos en caché: ' +
        error.message
      );
    }
  }

  const categoriaBuscada =
    normalizar_(categoriaSeleccionada);

  return productos.filter(producto =>
    !categoriaBuscada ||
    normalizar_(producto.categoria) ===
      categoriaBuscada
  );
}


function obtenerEstadoCategoriasMensuales(
  puntoVenta,
  fecha
) {
  const punto =
    limpiarTextoMensual_(puntoVenta);

  const fechaBuscada =
    claveFechaMensual_(fecha);

  if (!punto || !fechaBuscada) {
    throw new Error(
      'Seleccione el punto de venta y la fecha.'
    );
  }

  const productos = obtenerProductos(punto);
  const categorias = {};
  const categoriasNormalizadas = {};

  productos.forEach(producto => {
    const nombre = producto.categoria;

    if (!categorias[nombre]) {
      categorias[nombre] = {
        categoria: nombre,
        totalProductos: 0,
        guardada: false
      };

      categoriasNormalizadas[
        normalizar_(nombre)
      ] = categorias[nombre];
    }

    categorias[nombre].totalProductos++;
  });

  const libro = obtenerLibroMensualPDV_(punto);
  const hoja = libro.getSheetByName(
    'Conteos Mensuales'
  );

  if (hoja && hoja.getLastRow() >= 2) {
    const registros = hoja
      .getRange(
        2,
        3,
        hoja.getLastRow() - 1,
        3
      )
      .getValues();

    registros.forEach(fila => {
      if (
        claveFechaMensual_(fila[0]) !==
          fechaBuscada ||
        normalizar_(fila[1]) !==
          normalizar_(punto)
      ) {
        return;
      }

      const categoriaGuardada =
        limpiarTextoMensual_(fila[2]);

      const categoriaEncontrada =
        categoriasNormalizadas[
          normalizar_(categoriaGuardada)
        ];

      if (categoriaEncontrada) {
        categoriaEncontrada.guardada = true;
      }
    });
  }

  return Object.values(categorias)
    .sort((a, b) =>
      a.categoria.localeCompare(
        b.categoria,
        'es'
      )
    );
}


function guardarInventario(datos) {
  validarInventarioMensual_(datos);
  validarIntegridadConteosMensuales_(datos);

  const convertirNumero = valor => {
    return Number(
      String(valor)
        .trim()
        .replace(',', '.')
    );
  };

  const idRegistro =
    Utilities.getUuid();

  const fechaHora =
    new Date();

  const filas =
    datos.conteos.map(conteo => {
      const cerrado =
        convertirNumero(conteo.cerrado);

      const abierto =
        convertirNumero(conteo.abierto);

      if (
        isNaN(cerrado) ||
        cerrado < 0
      ) {
        throw new Error(
          'La cantidad cerrada del ítem ' +
          conteo.item +
          ' no es válida.'
        );
      }

      if (
        isNaN(abierto) ||
        abierto < 0
      ) {
        throw new Error(
          'La cantidad abierta del ítem ' +
          conteo.item +
          ' no es válida.'
        );
      }

      return [
        idRegistro,
        fechaHora,
        datos.fecha,
        datos.puntoVenta,
        datos.categoria,
        conteo.item,
        conteo.producto,
        conteo.udm,
        cerrado,
        abierto,
        cerrado + abierto
      ];
    });

  // Abrir el archivo puede tardar. Se hace antes del bloqueo para que
  // los demás PDV no tengan que esperar durante esta consulta.
  const libro =
    obtenerLibroMensualPDV_(
      datos.puntoVenta
    );

  const bloqueo =
    LockService.getScriptLock();

  bloqueo.waitLock(30000);

  try {
    const nombreHoja =
      'Conteos Mensuales';

    let hojaDestino =
      libro.getSheetByName(
        nombreHoja
      );

    if (!hojaDestino) {
      hojaDestino =
        libro.insertSheet(
          nombreHoja
        );
    }

    const encabezados = [
      'ID Registro',
      'Fecha y hora',
      'Fecha inventario',
      'Punto de venta',
      'Categoría',
      'Item',
      'Nombre Producto',
      'Desc. U.M.',
      'Cerrado',
      'Abierto',
      'Total'
    ];

    const ultimaFila =
      hojaDestino.getLastRow();

    // Los encabezados y su formato solo se crean una vez.
    // Antes se reescribían en cada guardado.
    if (ultimaFila === 0) {
      prepararEncabezadosMensuales_(
        hojaDestino,
        encabezados
      );
    }

    if (
      categoriaMensualYaGuardada_(
        hojaDestino,
        datos
      )
    ) {
      throw new Error(
        'La categoría "' +
        datos.categoria +
        '" ya fue guardada para ' +
        datos.puntoVenta +
        ' en esta fecha.'
      );
    }

    hojaDestino
      .getRange(
        hojaDestino.getLastRow() + 1,
        1,
        filas.length,
        filas[0].length
      )
      .setValues(filas);

  } finally {
    bloqueo.releaseLock();
  }

  return {
    correcto: true,
    mensaje:
      'Inventario mensual guardado correctamente.',
    registros: filas.length
  };
}


function validarInventarioMensual_(datos) {
  if (
    !datos ||
    !datos.puntoVenta ||
    !datos.fecha ||
    !datos.categoria
  ) {
    throw new Error(
      'Debe seleccionar el PDV, ' +
      'la fecha y la categoría.'
    );
  }

  if (
    !Array.isArray(datos.conteos) ||
    datos.conteos.length === 0
  ) {
    throw new Error(
      'No se recibieron productos.'
    );
  }

  const incompleto =
    datos.conteos.find(conteo =>
      conteo.cerrado === '' ||
      conteo.cerrado === null ||
      conteo.cerrado === undefined ||
      conteo.abierto === '' ||
      conteo.abierto === null ||
      conteo.abierto === undefined
    );

  if (incompleto) {
    throw new Error(
      'Debe completar Cerrado y Abierto ' +
      'en todos los productos. ' +
      'Revise el ítem ' +
      incompleto.item +
      '.'
    );
  }
}


function obtenerLibroMensualPDV_(
  puntoVenta
) {
  const cache =
    CacheService.getScriptCache();

  const claveCache =
    crearClaveCacheMensual_(
      'archivo',
      puntoVenta
    );

  const idEnCache =
    cache.get(claveCache);

  if (idEnCache) {
    try {
      return SpreadsheetApp.openById(
        idEnCache
      );
    } catch (error) {
      cache.remove(claveCache);
    }
  }

  const carpeta =
    obtenerCarpetaBasesMensuales_();

  const archivos =
    carpeta.getFilesByName(
      puntoVenta
    );

  while (archivos.hasNext()) {
    const archivo = archivos.next();

    if (
      archivo.getMimeType() ===
      'application/vnd.google-apps.spreadsheet'
    ) {
      cache.put(
        claveCache,
        archivo.getId(),
        CACHE_ARCHIVO_SEGUNDOS
      );

      return SpreadsheetApp.openById(
        archivo.getId()
      );
    }
  }

  throw new Error(
    'No se encontró la base mensual de ' +
    puntoVenta + '.'
  );
}


function validarIntegridadConteosMensuales_(datos) {
  // La lista normalmente ya está en caché porque fue la misma que se
  // mostró en la página. Así se valida todo sin volver lento el guardado.
  const productosEsperados =
    obtenerProductos(
      datos.puntoVenta,
      datos.categoria
    );

  if (
    datos.conteos.length !==
    productosEsperados.length
  ) {
    throw new Error(
      'No se guardó el inventario porque la cantidad de productos ' +
      'recibida no coincide con la categoría. Actualice la página ' +
      'y vuelva a intentarlo.'
    );
  }

  const cantidadesEsperadas = {};

  productosEsperados.forEach(producto => {
    const clave =
      crearClaveProductoMensual_(producto);

    cantidadesEsperadas[clave] =
      (cantidadesEsperadas[clave] || 0) + 1;
  });

  datos.conteos.forEach(conteo => {
    const clave =
      crearClaveProductoMensual_(conteo);

    if (!cantidadesEsperadas[clave]) {
      throw new Error(
        'No se guardó el inventario porque falta un producto o ' +
        'se recibió uno diferente. Actualice la página y vuelva ' +
        'a intentarlo.'
      );
    }

    cantidadesEsperadas[clave]--;
  });

  const faltaProducto =
    Object.keys(cantidadesEsperadas)
      .some(clave =>
        cantidadesEsperadas[clave] !== 0
      );

  if (faltaProducto) {
    throw new Error(
      'No se guardó el inventario porque no llegaron todos los ' +
      'productos. Actualice la página y vuelva a intentarlo.'
    );
  }
}


function crearClaveProductoMensual_(producto) {
  return [
    producto && producto.item,
    producto && producto.producto,
    producto && producto.udm
  ]
    .map(normalizar_)
    .join('\u001F');
}


function crearClaveCacheMensual_(
  tipo,
  valor
) {
  const resumen =
    Utilities.computeDigest(
      Utilities.DigestAlgorithm.MD5,
      String(valor || ''),
      Utilities.Charset.UTF_8
    )
      .map(byte =>
        (byte + 256)
          .toString(16)
          .slice(-2)
      )
      .join('');

  return 'mensual:' + tipo + ':' + resumen;
}


function categoriaMensualYaGuardada_(
  hoja,
  datos
) {
  if (hoja.getLastRow() < 2) {
    return false;
  }

  const registros =
    hoja
      .getRange(
        2,
        3,
        hoja.getLastRow() - 1,
        3
      )
      .getValues();

  return registros.some(fila =>
    claveFechaMensual_(fila[0]) ===
      claveFechaMensual_(datos.fecha) &&

    normalizar_(fila[1]) ===
      normalizar_(datos.puntoVenta) &&

    normalizar_(fila[2]) ===
      normalizar_(datos.categoria)
  );
}


function generarDescargaConteosMensuales(
  filtros
) {
  validarAccesoAdministrador_();

  const fecha =
    claveFechaMensual_(
      filtros && filtros.fecha
    );

  const puntoVenta =
    limpiarTextoMensual_(
      filtros && filtros.puntoVenta
    );

  if (!fecha) {
    throw new Error(
      'Seleccione la fecha del inventario.'
    );
  }

  const carpeta =
    obtenerCarpetaBasesMensuales_();

  const archivos = carpeta.getFiles();
  const registros = [];

  while (archivos.hasNext()) {
    const archivo = archivos.next();

    if (
      archivo.getMimeType() !==
      'application/vnd.google-apps.spreadsheet'
    ) {
      continue;
    }

    if (
      puntoVenta &&
      normalizar_(archivo.getName()) !==
        normalizar_(puntoVenta)
    ) {
      continue;
    }

    const libro =
      SpreadsheetApp.openById(
        archivo.getId()
      );

    const hoja =
      libro.getSheetByName(
        'Conteos Mensuales'
      );

    if (!hoja || hoja.getLastRow() < 2) {
      continue;
    }

    const datos = hoja
      .getRange(
        2,
        1,
        hoja.getLastRow() - 1,
        11
      )
      .getDisplayValues();

    datos.forEach(fila => {
      if (
        claveFechaMensual_(fila[2]) !==
        fecha
      ) {
        return;
      }

      registros.push([
        fila[2],
        fila[3],
        fila[4],
        formatearItemSiesa_(fila[5]),
        fila[6],
        fila[7],
        fila[8],
        fila[9],
        fila[10]
      ]);
    });
  }

  if (registros.length === 0) {
    throw new Error(
      'No se encontraron conteos mensuales ' +
      'para la fecha y el PDV seleccionados.'
    );
  }

  registros.sort((a, b) => {
    return (
      String(a[1]).localeCompare(
        String(b[1]),
        'es'
      ) ||
      String(a[2]).localeCompare(
        String(b[2]),
        'es'
      ) ||
      String(a[3]).localeCompare(
        String(b[3]),
        'es'
      )
    );
  });

  const encabezados = [
    'Fecha inventario',
    'Punto de venta',
    'Categoría',
    'Item Siesa',
    'Nombre Producto',
    'Desc. U.M.',
    'Cerrado',
    'Abierto',
    'Total'
  ];

  const contenido =
    '\uFEFF' +
    [encabezados]
      .concat(registros)
      .map(fila =>
        fila
          .map(escaparCampoCSV_)
          .join(';')
      )
      .join('\r\n');

  const nombrePDV = puntoVenta
    ? '_' + nombreArchivoSeguro_(puntoVenta)
    : '_Todos_los_PDV';

  return {
    nombre:
      'Conteos_Mensuales_' +
      fecha +
      nombrePDV +
      '.csv',
    tipo: 'text/csv;charset=utf-8',
    contenidoBase64:
      Utilities.base64Encode(
        Utilities.newBlob(
          contenido,
          'text/csv'
        ).getBytes()
      ),
    registros: registros.length
  };
}


function generarPlanoSiesaMensual(datosPlano) {
  validarAccesoAdministrador_();

  const fecha =
    claveFechaMensual_(
      datosPlano && datosPlano.fecha
    );

  const puntoVenta =
    limpiarTextoMensual_(
      datosPlano && datosPlano.puntoVenta
    );

  const bodega =
    limpiarTextoMensual_(
      datosPlano && datosPlano.bodega
    ).toUpperCase();

  const consecutivoIngresado =
    limpiarTextoMensual_(
      datosPlano && datosPlano.consecutivo
    );

  if (!fecha) {
    throw new Error(
      'Seleccione la fecha del inventario.'
    );
  }

  if (!puntoVenta) {
    throw new Error(
      'Seleccione un punto de venta.'
    );
  }

  if (!/^[A-Z0-9]{4}$/.test(bodega)) {
    throw new Error(
      'La bodega debe tener 4 caracteres. ' +
      'Ejemplo: BR03.'
    );
  }

  if (!/^\d{1,8}$/.test(consecutivoIngresado)) {
    throw new Error(
      'El consecutivo debe contener solamente ' +
      'números y tener máximo 8 dígitos.'
    );
  }

  const consecutivo =
    consecutivoIngresado.padStart(8, '0');

  const libro =
    obtenerLibroMensualPDV_(puntoVenta);

  const hoja =
    libro.getSheetByName('Conteos Mensuales');

  if (!hoja || hoja.getLastRow() < 2) {
    throw new Error(
      'El PDV seleccionado no tiene conteos mensuales.'
    );
  }

  const filas = hoja
    .getRange(
      2,
      1,
      hoja.getLastRow() - 1,
      11
    )
    .getValues()
    .filter(fila =>
      claveFechaMensual_(fila[2]) === fecha &&
      normalizar_(fila[3]) ===
        normalizar_(puntoVenta)
    );

  if (filas.length === 0) {
    throw new Error(
      'No se encontraron conteos de ' +
      puntoVenta + ' para la fecha seleccionada.'
    );
  }

  if (filas.length > 9999997) {
    throw new Error(
      'El plano supera la cantidad máxima de registros.'
    );
  }

  const lineas = [
    '000000100000001009'
  ];

  filas.forEach((fila, indice) => {
    const item =
      formatearItemPlanoSiesa_(fila[5]);

    const cantidad =
      formatearCantidadPlanoSiesa_(
        fila[10],
        item
      );

    const numeroLinea =
      String(indice + 2).padStart(7, '0');

    const linea =
      numeroLinea +
      '04120002009' +
      consecutivo +
      ' '.repeat(55) +
      bodega +
      ' '.repeat(26) +
      '00000' +
      cantidad.cerosIniciales +
      cantidad.valor +
      cantidad.cerosFinales +
      item +
      '0'.repeat(39) +
      item +
      ' '.repeat(60);

    if (linea.length !== 333) {
      throw new Error(
        'No fue posible formar el registro del ítem ' +
        item + '.'
      );
    }

    lineas.push(linea);
  });

  const numeroCierre =
    String(lineas.length + 1).padStart(7, '0');

  lineas.push(
    numeroCierre + '99990001009'
  );

  const contenido = lineas.join('\r\n');

  const nombrePDV =
    nombrePDVPlanoSiesa_(puntoVenta);

  return {
    nombre:
      nombrePDV +
      '-Mensual-' +
      consecutivo +
      '-PlanosPDV.txt',
    tipo: 'text/plain;charset=us-ascii',
    contenidoBase64:
      Utilities.base64Encode(
        Utilities.newBlob(
          contenido,
          'text/plain'
        ).getBytes()
      ),
    registros: filas.length,
    consecutivo: consecutivo,
    bodega: bodega
  };
}


function formatearItemPlanoSiesa_(valor) {
  const texto =
    limpiarTextoMensual_(valor)
      .replace(/\.0+$/, '');

  if (!/^\d{1,11}$/.test(texto)) {
    throw new Error(
      'El ítem "' + texto +
      '" no es válido para el plano Siesa.'
    );
  }

  return texto.padStart(11, '0');
}


function formatearCantidadPlanoSiesa_(
  valor,
  item
) {
  const numero =
    convertirNumeroPlanoSiesa_(valor);

  if (!isFinite(numero) || numero < 0) {
    throw new Error(
      'La cantidad total del ítem ' +
      item + ' no es válida.'
    );
  }

  const partes = numero
    .toFixed(15)
    .split('.');

  if (partes[0].length > 15) {
    throw new Error(
      'La cantidad del ítem ' + item +
      ' supera el tamaño permitido por Siesa.'
    );
  }

  return {
    cerosIniciales:
      '000000000000000.' +
      '000000000000000.',
    valor:
      partes[0].padStart(15, '0') +
      '.' +
      partes[1].padEnd(15, '0') +
      '.',
    cerosFinales:
      '000000000000000.' +
      '000000000000000.'
  };
}


function convertirNumeroPlanoSiesa_(valor) {
  if (typeof valor === 'number') {
    return valor;
  }

  let texto =
    limpiarTextoMensual_(valor)
      .replace(/\s/g, '');

  if (
    texto.includes(',') &&
    texto.includes('.')
  ) {
    if (
      texto.lastIndexOf(',') >
      texto.lastIndexOf('.')
    ) {
      texto = texto
        .replace(/\./g, '')
        .replace(',', '.');
    } else {
      texto = texto.replace(/,/g, '');
    }
  } else if (texto.includes(',')) {
    texto = texto.replace(',', '.');
  }

  return Number(texto);
}


function nombrePDVPlanoSiesa_(puntoVenta) {
  let nombre = limpiarTextoMensual_(puntoVenta);

  nombre = nombre.replace(
    /^[A-Z]{1,4}\d{1,3}\s*[-–]\s*/i,
    ''
  );

  return nombreArchivoSeguro_(nombre)
    .toUpperCase() || 'PDV';
}


function obtenerConteoConsolidadoPDV(filtros) {
  validarAccesoAdministrador_();

  const fecha = claveFechaMensual_(
    filtros && filtros.fecha
  );

  const puntoVenta = limpiarTextoMensual_(
    filtros && filtros.puntoVenta
  );

  if (!fecha) {
    throw new Error(
      'Seleccione la fecha del inventario.'
    );
  }

  if (!puntoVenta) {
    throw new Error(
      'Seleccione un punto de venta.'
    );
  }

  const libro = obtenerLibroMensualPDV_(
    puntoVenta
  );

  const hoja = libro.getSheetByName(
    'Conteos Mensuales'
  );

  if (!hoja || hoja.getLastRow() < 2) {
    throw new Error(
      'El PDV seleccionado no tiene conteos mensuales.'
    );
  }

  const filas = hoja
    .getRange(
      2,
      1,
      hoja.getLastRow() - 1,
      11
    )
    .getValues()
    .filter(fila =>
      claveFechaMensual_(fila[2]) === fecha &&
      normalizar_(fila[3]) ===
        normalizar_(puntoVenta)
    );

  if (filas.length === 0) {
    throw new Error(
      'No se encontraron conteos de ' +
      puntoVenta + ' para la fecha seleccionada.'
    );
  }

  const consolidado = {};

  filas.forEach(fila => {
    const item = formatearItemSiesa_(fila[5]);
    const clave = item + '|' +
      normalizar_(fila[6]) + '|' +
      normalizar_(fila[7]);

    if (!consolidado[clave]) {
      consolidado[clave] = {
        item: item,
        producto: limpiarTextoMensual_(fila[6]),
        udm: limpiarTextoMensual_(fila[7]),
        categorias: [],
        cerrado: 0,
        abierto: 0,
        total: 0
      };
    }

    const categoria = limpiarTextoMensual_(fila[4]);

    if (
      categoria &&
      !consolidado[clave].categorias.includes(
        categoria
      )
    ) {
      consolidado[clave].categorias.push(categoria);
    }

    consolidado[clave].cerrado +=
      convertirNumeroPlanoSiesa_(fila[8]) || 0;
    consolidado[clave].abierto +=
      convertirNumeroPlanoSiesa_(fila[9]) || 0;
    consolidado[clave].total +=
      convertirNumeroPlanoSiesa_(fila[10]) || 0;
  });

  const registros = Object.values(consolidado)
    .map(registro => ({
      item: registro.item,
      producto: registro.producto,
      categoria: registro.categorias.join(', '),
      udm: registro.udm,
      cerrado: redondearConteoMensual_(
        registro.cerrado
      ),
      abierto: redondearConteoMensual_(
        registro.abierto
      ),
      total: redondearConteoMensual_(
        registro.total
      )
    }))
    .sort((a, b) =>
      String(a.item).localeCompare(
        String(b.item),
        'es',
        { numeric: true }
      )
    );

  return {
    puntoVenta: puntoVenta,
    fecha: fecha,
    registros: registros
  };
}


function redondearConteoMensual_(valor) {
  return Math.round(
    (Number(valor) + Number.EPSILON) * 1000000
  ) / 1000000;
}


function formatearItemSiesa_(valor) {
  const texto =
    limpiarTextoMensual_(valor);

  return /^\d+$/.test(texto)
    ? texto.padStart(8, '0')
    : texto;
}


function escaparCampoCSV_(valor) {
  return '"' +
    String(
      valor === null ||
      valor === undefined
        ? ''
        : valor
    ).replace(/"/g, '""') +
    '"';
}


function nombreArchivoSeguro_(valor) {
  return String(valor || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_-]+/g, '_')
    .replace(/^_+|_+$/g, '');
}


function prepararEncabezadosMensuales_(
  hoja,
  encabezados
) {
  hoja
    .getRange(
      1,
      1,
      1,
      encabezados.length
    )
    .setValues([encabezados])
    .setBackground('#4A2B14')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold');

  hoja.setFrozenRows(1);
}


function buscarIndiceMensual_(
  encabezados,
  opciones
) {
  const opcionesNormalizadas =
    opciones.map(normalizar_);

  return encabezados.findIndex(
    encabezado =>
      opcionesNormalizadas.includes(
        encabezado
      )
  );
}


function limpiarTextoMensual_(valor) {
  return String(
    valor === null ||
    valor === undefined
      ? ''
      : valor
  ).trim();
}


function claveFechaMensual_(valor) {
  if (
    valor instanceof Date &&
    !isNaN(valor.getTime())
  ) {
    return Utilities.formatDate(
      valor,
      Session.getScriptTimeZone(),
      'yyyy-MM-dd'
    );
  }

  const texto =
    String(valor || '').trim();

  if (
    /^\d{4}-\d{2}-\d{2}$/.test(
      texto
    )
  ) {
    return texto;
  }

  const partes =
    texto.match(
      /^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/
    );

  if (partes) {
    return (
      partes[3] +
      '-' +
      String(partes[2])
        .padStart(2, '0') +
      '-' +
      String(partes[1])
        .padStart(2, '0')
    );
  }

  return texto;
}


function probarConexionMensual() {
  const puntosVenta =
    obtenerPuntosVenta();

  console.log(
    'PDV ENCONTRADOS: ' +
    puntosVenta.length
  );

  if (puntosVenta.length === 0) {
    throw new Error(
      'No se encontraron bases mensuales.'
    );
  }

  const primerPDV =
    puntosVenta[0];

  const categorias =
    obtenerCategorias(primerPDV);

  console.log(
    'PDV DE PRUEBA: ' +
    primerPDV
  );

  console.log(
    'CATEGORÍAS: ' +
    categorias.join(' | ')
  );

  console.log(
    'TOTAL CATEGORÍAS: ' +
    categorias.length
  );
}
function probarProductosMensuales() {
  const puntoVenta =
    'BC01 - Cocina Envigado';

  const categorias =
    obtenerCategorias(puntoVenta);

  let totalProductos = 0;

  categorias.forEach(categoria => {
    const productos =
      obtenerProductos(
        puntoVenta,
        categoria
      );

    totalProductos +=
      productos.length;

    console.log(
      categoria +
      ': ' +
      productos.length +
      ' productos'
    );
  });

  console.log(
    'TOTAL DE PRODUCTOS: ' +
    totalProductos
  );
}


/* =====================================================
   LIMPIEZA AUTOMÁTICA DE CONTEOS
   Conserva las bases, productos y categorías.
   Elimina únicamente registros guardados hace más de 5 días.
   ===================================================== */


function instalarLimpiezaAutomaticaMensual() {
  const nombreFuncion =
    'limpiarConteosMensualesVencidos';

  ScriptApp.getProjectTriggers()
    .filter(trigger =>
      trigger.getHandlerFunction() ===
        nombreFuncion
    )
    .forEach(trigger =>
      ScriptApp.deleteTrigger(trigger)
    );

  ScriptApp
    .newTrigger(nombreFuncion)
    .timeBased()
    .everyDays(1)
    .atHour(HORA_LIMPIEZA_AUTOMATICA)
    .create();

  const resultado =
    limpiarConteosMensualesVencidos();

  console.log(
    'LIMPIEZA AUTOMÁTICA INSTALADA. ' +
    'Se ejecutará diariamente alrededor de las ' +
    HORA_LIMPIEZA_AUTOMATICA + ':00.'
  );

  return {
    instalada: true,
    hora: HORA_LIMPIEZA_AUTOMATICA,
    resultadoInicial: resultado
  };
}


function limpiarConteosMensualesVencidos() {
  const bloqueo =
    LockService.getScriptLock();

  bloqueo.waitLock(30000);

  try {
    const limite = new Date(
      Date.now() -
      DIAS_RETENCION_CONTEOS_MENSUALES *
        24 * 60 * 60 * 1000
    );

    const carpeta =
      obtenerCarpetaBasesMensuales_();

    const archivos = carpeta.getFiles();
    let puntosRevisados = 0;
    let puntosLimpiados = 0;
    let registrosEliminados = 0;
    const errores = [];

    while (archivos.hasNext()) {
      const archivo = archivos.next();

      if (
        archivo.getMimeType() !==
        'application/vnd.google-apps.spreadsheet'
      ) {
        continue;
      }

      puntosRevisados++;

      try {
        const libro = SpreadsheetApp.openById(
          archivo.getId()
        );

        const hoja = libro.getSheetByName(
          'Conteos Mensuales'
        );

        if (!hoja || hoja.getLastRow() < 2) {
          continue;
        }

        const ultimaFila = hoja.getLastRow();
        const cantidadFilas = ultimaFila - 1;
        const rango = hoja.getRange(
          2,
          1,
          cantidadFilas,
          11
        );

        const registros = rango.getValues();
        const vigentes = [];
        let eliminadosPDV = 0;

        registros.forEach(fila => {
          const fechaGuardado = fila[1];

          if (
            fechaGuardado instanceof Date &&
            !isNaN(fechaGuardado.getTime()) &&
            fechaGuardado.getTime() <
              limite.getTime()
          ) {
            eliminadosPDV++;
            return;
          }

          // Las filas sin una fecha válida se conservan para evitar
          // eliminar información que no pueda verificarse con seguridad.
          vigentes.push(fila);
        });

        if (eliminadosPDV === 0) {
          continue;
        }

        // Se reescribe una sola vez para no borrar fila por fila ni
        // consumir tiempo mientras los PDV usan el aplicativo.
        rango.clearContent();

        if (vigentes.length > 0) {
          hoja
            .getRange(
              2,
              1,
              vigentes.length,
              11
            )
            .setValues(vigentes);
        }

        puntosLimpiados++;
        registrosEliminados += eliminadosPDV;

      } catch (error) {
        errores.push(
          archivo.getName() + ': ' +
          error.message
        );
      }
    }

    const resultado = {
      correcto: errores.length === 0,
      puntosRevisados: puntosRevisados,
      puntosLimpiados: puntosLimpiados,
      registrosEliminados:
        registrosEliminados,
      antiguedadDias:
        DIAS_RETENCION_CONTEOS_MENSUALES,
      errores: errores
    };

    console.log(
      'LIMPIEZA MENSUAL: ' +
      JSON.stringify(resultado)
    );

    return resultado;

  } finally {
    bloqueo.releaseLock();
  }
}


function desinstalarLimpiezaAutomaticaMensual() {
  const nombreFuncion =
    'limpiarConteosMensualesVencidos';

  let eliminados = 0;

  ScriptApp.getProjectTriggers()
    .filter(trigger =>
      trigger.getHandlerFunction() ===
        nombreFuncion
    )
    .forEach(trigger => {
      ScriptApp.deleteTrigger(trigger);
      eliminados++;
    });

  return {
    instalada: false,
    disparadoresEliminados: eliminados
  };
}
