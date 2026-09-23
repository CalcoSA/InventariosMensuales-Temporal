
    let productos = [];
    let puntoVentaActual = '';
    let fechaActual = '';
    let categoriaActual = '';
    let conteoConsolidado = [];
    let estadosCategorias = [];
    let temporizadorBorrador = null;
    let temporizadorBusqueda = null;
    let actualizacionProgresoPendiente = false;
    let guardandoInventario = false;

    document.addEventListener(
      'DOMContentLoaded',
      function () {
        asignarFechaActual();
        cargarPuntosVenta();
        verificarAdministrador();

        document.addEventListener(
          'visibilitychange',
          function () {
            if (document.hidden && productos.length) {
              guardarBorradorAhora();
            }
          }
        );

        window.addEventListener(
          'beforeunload',
          function () {
            if (productos.length) {
              guardarBorradorAhora();
            }
          }
        );
      }
    );

    function asignarFechaActual() {
      const hoy = new Date();
      const anio = hoy.getFullYear();

      const mes = String(
        hoy.getMonth() + 1
      ).padStart(2, '0');

      const dia = String(
        hoy.getDate()
      ).padStart(2, '0');

      document
        .getElementById('fechaInventario')
        .value =
          anio + '-' + mes + '-' + dia;

      document
        .getElementById('adminFecha')
        .value =
          anio + '-' + mes + '-' + dia;
    }

    function cargarPuntosVenta() {
      monthlyApi
        .withSuccessHandler(function (puntos) {
          const selector =
            document.getElementById('puntoVenta');

          selector.innerHTML =
            '<option value="">' +
            'Seleccione un punto de venta' +
            '</option>';

          puntos.forEach(function (punto) {
            const opcion =
              document.createElement('option');

            opcion.value = punto;
            opcion.textContent = punto;
            selector.appendChild(opcion);
          });

          cargarPuntosAdministrador(puntos);

          if (puntos.length === 0) {
            mostrarMensaje(
              'mensajeInicio',
              'No se encontraron puntos de venta disponibles.',
              'error'
            );
          }
        })
        .withFailureHandler(function (error) {
          mostrarMensaje(
            'mensajeInicio',
            obtenerMensajeError(error),
            'error'
          );
        })
        .obtenerPuntosVenta();
    }

    function verificarAdministrador() {
      monthlyApi
        .withSuccessHandler(function (estado) {
          if (
            estado &&
            estado.esAdministrador
          ) {
            document
              .getElementById('botonAdministracion')
              .classList.remove('oculto');
          }
        })
        .withFailureHandler(function () {
          document
            .getElementById('botonAdministracion')
            .classList.add('oculto');
        })
        .obtenerEstadoAdministrador();
    }

    function cargarPuntosAdministrador(puntos) {
      const selector =
        document.getElementById('adminPuntoVenta');

      selector.innerHTML =
        '<option value="">' +
        'Seleccione un punto de venta' +
        '</option>';

      puntos.forEach(function (punto) {
        const opcion =
          document.createElement('option');

        opcion.value = punto;
        opcion.textContent = punto;
        selector.appendChild(opcion);
      });
    }

    function abrirAdministracion() {
      [
        'pantallaInicio',
        'pantallaCarga',
        'pantallaInventario',
        'pantallaExito',
        'pantallaConsolidado'
      ].forEach(function (id) {
        document
          .getElementById(id)
          .classList.add('oculto');
      });

      ocultarMensaje('mensajeAdministracion');

      document
        .getElementById('pantallaAdministracion')
        .classList.remove('oculto');

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }

    function cerrarAdministracion() {
      document
        .getElementById('pantallaAdministracion')
        .classList.add('oculto');

      document
        .getElementById('pantallaInicio')
        .classList.remove('oculto');

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }

    function abrirConteoConsolidado() {
      ocultarMensaje('mensajeAdministracion');

      const fecha =
        document.getElementById('adminFecha').value;

      const puntoVenta =
        document
          .getElementById('adminPuntoVenta')
          .value;

      if (!fecha || !puntoVenta) {
        mostrarMensaje(
          'mensajeAdministracion',
          'Seleccione la fecha y un punto de venta.',
          'error'
        );
        return;
      }

      const boton =
        document.getElementById('botonVerConteo');

      boton.disabled = true;
      boton.textContent = 'Cargando conteo...';

      monthlyApi
        .withSuccessHandler(function (resultado) {
          boton.disabled = false;
          boton.textContent = 'Ver conteo del PDV';
          conteoConsolidado = resultado.registros || [];

          document
            .getElementById('datosConteoConsolidado')
            .textContent =
              resultado.puntoVenta +
              ' · Fecha: ' +
              formatearFechaVisible(resultado.fecha);

          document
            .getElementById('buscadorConteo')
            .value = '';

          actualizarResumenConteo(conteoConsolidado);
          renderizarConteoConsolidado(
            conteoConsolidado
          );

          document
            .getElementById('pantallaAdministracion')
            .classList.add('oculto');

          document
            .getElementById('pantallaConsolidado')
            .classList.remove('oculto');

          window.scrollTo({ top: 0 });
        })
        .withFailureHandler(function (error) {
          boton.disabled = false;
          boton.textContent = 'Ver conteo del PDV';

          mostrarMensaje(
            'mensajeAdministracion',
            obtenerMensajeError(error),
            'error'
          );
        })
        .obtenerConteoConsolidadoPDV({
          fecha: fecha,
          puntoVenta: puntoVenta
        });
    }

    function filtrarConteoConsolidado() {
      const busqueda = normalizarBusqueda(
        document
          .getElementById('buscadorConteo')
          .value
      );

      const filtrados = conteoConsolidado.filter(
        function (registro) {
          return normalizarBusqueda(
            registro.item + ' ' + registro.producto
          ).includes(busqueda);
        }
      );

      renderizarConteoConsolidado(filtrados);
    }

    function renderizarConteoConsolidado(registros) {
      const cuerpo = document.getElementById(
        'cuerpoConteoConsolidado'
      );

      cuerpo.innerHTML = '';

      if (registros.length === 0) {
        const fila = cuerpo.insertRow();
        const celda = fila.insertCell();
        celda.colSpan = 7;
        celda.className = 'sin-resultados';
        celda.textContent =
          'No se encontraron productos.';
        return;
      }

      registros.forEach(function (registro) {
        const fila = cuerpo.insertRow();

        agregarCeldaConteo(fila, registro.item);
        agregarCeldaConteo(fila, registro.producto);
        agregarCeldaConteo(fila, registro.categoria);
        agregarCeldaConteo(fila, registro.udm);
        agregarCeldaConteo(
          fila,
          formatearNumeroConteo(registro.cerrado),
          'numero'
        );
        agregarCeldaConteo(
          fila,
          formatearNumeroConteo(registro.abierto),
          'numero'
        );
        agregarCeldaConteo(
          fila,
          formatearNumeroConteo(registro.total),
          'numero'
        );
      });
    }

    function agregarCeldaConteo(fila, valor, clase) {
      const celda = fila.insertCell();
      celda.textContent = valor;

      if (clase) {
        celda.className = clase;
      }
    }

    function actualizarResumenConteo(registros) {
      const totales = registros.reduce(
        function (acumulado, registro) {
          acumulado.cerrado +=
            Number(registro.cerrado) || 0;
          acumulado.abierto +=
            Number(registro.abierto) || 0;
          acumulado.total +=
            Number(registro.total) || 0;
          return acumulado;
        },
        { cerrado: 0, abierto: 0, total: 0 }
      );

      document.getElementById(
        'resumenProductos'
      ).textContent = registros.length;

      document.getElementById(
        'resumenCerrado'
      ).textContent =
        formatearNumeroConteo(totales.cerrado);

      document.getElementById(
        'resumenAbierto'
      ).textContent =
        formatearNumeroConteo(totales.abierto);

      document.getElementById(
        'resumenTotal'
      ).textContent =
        formatearNumeroConteo(totales.total);
    }

    function volverAdministracion() {
      document
        .getElementById('pantallaConsolidado')
        .classList.add('oculto');

      document
        .getElementById('pantallaAdministracion')
        .classList.remove('oculto');

      window.scrollTo({ top: 0 });
    }

    function normalizarBusqueda(valor) {
      return String(valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
    }

    function formatearNumeroConteo(valor) {
      return new Intl.NumberFormat(
        'es-CO',
        { maximumFractionDigits: 6 }
      ).format(Number(valor) || 0);
    }

    function formatearFechaVisible(fecha) {
      const partes = String(fecha).split('-');

      return partes.length === 3
        ? partes[2] + '/' + partes[1] + '/' + partes[0]
        : fecha;
    }

    function descargarConteosMensuales() {
      ocultarMensaje('mensajeAdministracion');

      const fecha =
        document.getElementById('adminFecha').value;

      const puntoVenta =
        document
          .getElementById('adminPuntoVenta')
          .value;

      if (!fecha || !puntoVenta) {
        mostrarMensaje(
          'mensajeAdministracion',
          'Seleccione la fecha y un punto de venta.',
          'error'
        );
        return;
      }

      const boton =
        document
          .getElementById('botonDescargarConteos');

      boton.disabled = true;
      boton.textContent = 'Preparando descarga...';

      monthlyApi
        .withSuccessHandler(function (archivo) {
          boton.disabled = false;
          boton.textContent = 'Descargar conteos CSV';

          descargarArchivoBase64(archivo);

          mostrarMensaje(
            'mensajeAdministracion',
            'Archivo descargado correctamente con ' +
              archivo.registros +
              ' registros.',
            'exito'
          );
        })
        .withFailureHandler(function (error) {
          boton.disabled = false;
          boton.textContent = 'Descargar conteos CSV';

          mostrarMensaje(
            'mensajeAdministracion',
            obtenerMensajeError(error),
            'error'
          );
        })
        .generarDescargaConteosMensuales({
          fecha: fecha,
          puntoVenta: puntoVenta
        });
    }

    function descargarPlanoSiesaMensual() {
      ocultarMensaje('mensajeAdministracion');

      const fecha =
        document.getElementById('adminFecha').value;

      const puntoVenta =
        document
          .getElementById('adminPuntoVenta')
          .value;

      const bodega =
        document
          .getElementById('adminBodega')
          .value
          .trim()
          .toUpperCase();

      const consecutivo =
        document
          .getElementById('adminConsecutivo')
          .value
          .trim();

      if (
        !fecha ||
        !puntoVenta ||
        !bodega ||
        !consecutivo
      ) {
        mostrarMensaje(
          'mensajeAdministracion',
          'Complete la fecha, el PDV, la bodega y el consecutivo.',
          'error'
        );
        return;
      }

      const boton =
        document.getElementById(
          'botonDescargarPlano'
        );

      boton.disabled = true;
      boton.textContent = 'Preparando plano...';

      monthlyApi
        .withSuccessHandler(function (archivo) {
          boton.disabled = false;
          boton.textContent = 'Descargar plano Siesa';

          descargarArchivoBase64(archivo);

          mostrarMensaje(
            'mensajeAdministracion',
            'Plano descargado correctamente con ' +
              archivo.registros +
              ' registros.',
            'exito'
          );
        })
        .withFailureHandler(function (error) {
          boton.disabled = false;
          boton.textContent = 'Descargar plano Siesa';

          mostrarMensaje(
            'mensajeAdministracion',
            obtenerMensajeError(error),
            'error'
          );
        })
        .generarPlanoSiesaMensual({
          fecha: fecha,
          puntoVenta: puntoVenta,
          bodega: bodega,
          consecutivo: consecutivo
        });
    }

    function descargarArchivoBase64(archivo) {
      const binario = atob(
        archivo.contenidoBase64
      );

      const bytes = new Uint8Array(
        binario.length
      );

      for (
        let posicion = 0;
        posicion < binario.length;
        posicion++
      ) {
        bytes[posicion] =
          binario.charCodeAt(posicion);
      }

      const blob = new Blob(
        [bytes],
        { type: archivo.tipo }
      );

      const enlace =
        document.createElement('a');

      const url =
        URL.createObjectURL(blob);

      enlace.href = url;
      enlace.download = archivo.nombre;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();

      setTimeout(function () {
        URL.revokeObjectURL(url);
      }, 1000);
    }

    function cargarCategoriasPDV() {
      const puntoVenta =
        document
          .getElementById('puntoVenta')
          .value;

      const fecha =
        document
          .getElementById('fechaInventario')
          .value;

      const selector =
        document
          .getElementById('categoriaInventario');

      const control =
        document.getElementById(
          'controlCategorias'
        );

      ocultarMensaje('mensajeInicio');
      selector.disabled = true;
      estadosCategorias = [];
      control.classList.add('oculto');

      if (!puntoVenta || !fecha) {
        selector.innerHTML =
          '<option value="">' +
          'Seleccione primero el PDV y la fecha' +
          '</option>';

        return;
      }

      selector.innerHTML =
        '<option value="">' +
        'Cargando categorías...' +
        '</option>';

      monthlyApi
        .withSuccessHandler(function (estados) {
          if (document.getElementById('puntoVenta').value !== puntoVenta ||
              document.getElementById('fechaInventario').value !== fecha) return;
          estadosCategorias = estados || [];

          selector.innerHTML =
            '<option value="">' +
            'Seleccione una categoría' +
            '</option>';

          estadosCategorias.forEach(function (estado) {
            const opcion =
              document.createElement('option');

            const estadoLocal =
              calcularEstadoCategoria(estado);

            opcion.value = estado.categoria;
            opcion.textContent =
              estado.categoria +
              ' — ' +
              etiquetaEstadoCategoria(estadoLocal);

            opcion.disabled = estado.guardada;
            selector.appendChild(opcion);
          });

          selector.disabled = false;
          mostrarEstadoCategorias();
          control.classList.remove('oculto');

          if (estadosCategorias.length === 0) {
            mostrarMensaje(
              'mensajeInicio',
              'No se encontraron categorías para este PDV.',
              'error'
            );
          }
        })
        .withFailureHandler(function (error) {
          selector.innerHTML =
            '<option value="">' +
            'No fue posible cargar' +
            '</option>';

          mostrarMensaje(
            'mensajeInicio',
            obtenerMensajeError(error),
            'error'
          );
        })
        .obtenerEstadoCategoriasMensuales(
          puntoVenta,
          fecha
        );
    }

    function calcularEstadoCategoria(estado) {
      if (estado.guardada) {
        return 'guardada';
      }

      let borrador = [];

      try {
        borrador = leerBorradorPara(
          document.getElementById('puntoVenta').value,
          document.getElementById('fechaInventario').value,
          estado.categoria
        );
      } catch (error) {
        borrador = [];
      }

      const tieneCantidades = borrador.some(
        registro =>
          (registro.cerrado != null && registro.cerrado !== '') ||
          (registro.abierto != null && registro.abierto !== '')
      );

      if (!tieneCantidades) {
        return 'pendiente';
      }

      return 'proceso';
    }

    function etiquetaEstadoCategoria(estado) {
      const etiquetas = {
        pendiente: 'Pendiente',
        proceso: 'En proceso',
        completada: 'Completada',
        guardada: 'Ya guardada'
      };

      return etiquetas[estado] || 'Pendiente';
    }

    function mostrarEstadoCategorias() {
      const contenedor = document.getElementById(
        'listaEstadosCategorias'
      );

      const selector = document.getElementById(
        'categoriaInventario'
      );

      contenedor.innerHTML = estadosCategorias
        .map(function (estado) {
          const estadoLocal =
            calcularEstadoCategoria(estado);

          const opcion = Array.from(selector.options)
            .find(elemento =>
              elemento.value === estado.categoria
            );

          if (opcion) {
            opcion.textContent =
              estado.categoria +
              ' — ' +
              etiquetaEstadoCategoria(estadoLocal);
            opcion.disabled = estado.guardada;
          }

          return `
            <div class="estado-categoria estado-${estadoLocal}">
              <span>${escaparHTML(estado.categoria)}</span>
              <span>${etiquetaEstadoCategoria(estadoLocal)}</span>
            </div>
          `;
        })
        .join('');
    }

    function comenzarInventario() {
      const puntoVenta =
        document
          .getElementById('puntoVenta')
          .value;

      const fecha =
        document
          .getElementById('fechaInventario')
          .value;

      const categoria =
        document
          .getElementById('categoriaInventario')
          .value;

      ocultarMensaje('mensajeInicio');

      if (!puntoVenta || !fecha || !categoria) {
        mostrarMensaje(
          'mensajeInicio',
          'Seleccione el punto de venta, la fecha y la categoría.',
          'error'
        );

        return;
      }

      cargarCategoriaInventario(
        puntoVenta,
        fecha,
        categoria
      );
    }

    function cargarCategoriaInventario(
      puntoVenta,
      fecha,
      categoria
    ) {
      puntoVentaActual = puntoVenta;
      fechaActual = fecha;
      categoriaActual = categoria;

      document
        .getElementById('pantallaInicio')
        .classList.add('oculto');

      document
        .getElementById('pantallaExito')
        .classList.add('oculto');

      document
        .getElementById('pantallaInventario')
        .classList.add('oculto');

      document
        .getElementById('pantallaCarga')
        .classList.remove('oculto');

      monthlyApi
        .withSuccessHandler(function (lista) {
          document
            .getElementById('pantallaCarga')
            .classList.add('oculto');

          if (!lista || lista.length === 0) {
            document
              .getElementById('pantallaInicio')
              .classList.remove('oculto');

            mostrarMensaje(
              'mensajeInicio',
              'La categoría seleccionada no contiene productos.',
              'error'
            );

            return;
          }

          productos = lista.map(function (producto) {
            producto.cerrado = '';
            producto.abierto = '';

            return producto;
          });

          recuperarBorrador();
          prepararInventario();

          document
            .getElementById('pantallaInventario')
            .classList.remove('oculto');
        })
        .withFailureHandler(function (error) {
          document
            .getElementById('pantallaCarga')
            .classList.add('oculto');

          document
            .getElementById('pantallaInicio')
            .classList.remove('oculto');

          mostrarMensaje(
            'mensajeInicio',
            obtenerMensajeError(error),
            'error'
          );
        })
        .obtenerProductos(
          puntoVentaActual,
          categoriaActual
        );
    }

    function prepararInventario() {
      document
        .getElementById('nombrePDV')
        .textContent = puntoVentaActual;

      document
        .getElementById('fechaResumen')
        .textContent =
          'Fecha: ' +
          formatearFecha(fechaActual);

      document
        .getElementById('categoriaResumen')
        .textContent =
          'Categoría: ' + categoriaActual;

      document
        .getElementById('buscador')
        .value = '';

      mostrarProductos();
      actualizarProgreso();
    }

    function mostrarProductos() {
      const texto = normalizarTexto(
        document
          .getElementById('buscador')
          .value
      );

      const resultados =
        productos.filter(function (producto) {
          const contenido = normalizarTexto(
            producto.item +
            ' ' +
            producto.producto
          );

          return contenido.includes(texto);
        });

      const contenedor =
        document.getElementById('listaProductos');

      if (resultados.length === 0) {
        contenedor.innerHTML =
          '<div class="sin-resultados">' +
          'No se encontraron productos con esa búsqueda.' +
          '</div>';

        return;
      }

      contenedor.innerHTML =
        resultados.map(function (producto) {
          const indice =
            productos.indexOf(producto);

          return `
            <article class="producto">
              <div>
                <span class="categoria">
                  ${escaparHTML(producto.categoria)}
                </span>

                <div class="nombre-producto">
                  ${escaparHTML(producto.producto)}
                </div>

                <div class="detalle-producto">
                  Código:
                  ${escaparHTML(producto.item)}
                  · Desc. U.M.:
                  ${escaparHTML(
                    producto.udm || 'Sin UDM'
                  )}
                </div>
              </div>

              <div class="cantidades">
                <div class="cantidad">
                  <label for="cerrado-${indice}">
                    Cerrado
                  </label>

                  <input
                    id="cerrado-${indice}"
                    type="number"
                    min="0"
                    step="any"
                    inputmode="decimal"
                    value="${escaparHTML(producto.cerrado)}"
                    data-oninput="registrarCantidad(
                      ${indice},
                      'cerrado',
                      this.value
                    )"
                    placeholder="0"
                  >
                </div>

                <div class="cantidad">
                  <label for="abierto-${indice}">
                    Abierto
                  </label>

                  <input
                    id="abierto-${indice}"
                    type="number"
                    min="0"
                    step="any"
                    inputmode="decimal"
                    value="${escaparHTML(producto.abierto)}"
                    data-oninput="registrarCantidad(
                      ${indice},
                      'abierto',
                      this.value
                    )"
                    placeholder="0"
                  >
                </div>
              </div>
            </article>
          `;
        }).join('');
    }

    function programarMostrarProductos() {
      if (temporizadorBusqueda) {
        clearTimeout(temporizadorBusqueda);
      }

      temporizadorBusqueda = setTimeout(
        function () {
          temporizadorBusqueda = null;
          mostrarProductos();
        },
        150
      );
    }

    function registrarCantidad(
      indice,
      tipo,
      valor
    ) {
      productos[indice][tipo] = valor;

      guardarBorrador();
      programarActualizacionProgreso();
    }

    function programarActualizacionProgreso() {
      if (actualizacionProgresoPendiente) {
        return;
      }

      actualizacionProgresoPendiente = true;

      window.requestAnimationFrame(function () {
        actualizacionProgresoPendiente = false;
        actualizarProgreso();
      });
    }

    function actualizarProgreso() {
      const completados =
        productos.filter(function (producto) {
          return (
            producto.cerrado !== '' &&
            producto.abierto !== ''
          );
        }).length;

      const total = productos.length;

      const porcentaje = total
        ? Math.round(
            (completados / total) * 100
          )
        : 0;

      document
        .getElementById('textoProgreso')
        .textContent =
          completados +
          ' de ' +
          total +
          ' (' +
          porcentaje +
          '%)';

      document
        .getElementById('barraProgreso')
        .style.width =
          porcentaje + '%';
    }

    function completarVaciosConCero() {
      const cantidadVacios =
        productos.reduce(
          function (total, producto) {
            return (
              total +
              (producto.cerrado === '' ? 1 : 0) +
              (producto.abierto === '' ? 1 : 0)
            );
          },
          0
        );

      if (cantidadVacios === 0) {
        return;
      }

      const confirmar = window.confirm(
        'Se marcarán ' +
        cantidadVacios +
        ' casillas vacías con valor 0. ' +
        '¿Desea continuar?'
      );

      if (!confirmar) {
        return;
      }

      productos.forEach(function (producto) {
        if (producto.cerrado === '') {
          producto.cerrado = '0';
        }

        if (producto.abierto === '') {
          producto.abierto = '0';
        }
      });

      guardarBorrador();
      mostrarProductos();
      actualizarProgreso();
    }

    function guardarProceso() {
      if (guardandoInventario) {
        return;
      }

      ocultarMensaje('mensajeInventario');

      const hayAvance = productos.some(
        producto =>
          producto.cerrado !== '' ||
          producto.abierto !== ''
      );

      if (!hayAvance) {
        mostrarMensaje(
          'mensajeInventario',
          'Ingrese al menos una cantidad antes de guardar el proceso.',
          'error'
        );

        return;
      }

      const categoriaGuardada = categoriaActual;

      if (!guardarBorradorAhora()) {
        mostrarMensaje(
          'mensajeInventario',
          'No se pudo guardar el borrador en este navegador. Conserve esta pantalla e intente nuevamente.',
          'error'
        );
        return;
      }
      productos = [];

      document
        .getElementById('categoriaInventario')
        .value = '';

      document
        .getElementById('pantallaInventario')
        .classList.add('oculto');

      document
        .getElementById('pantallaInicio')
        .classList.remove('oculto');

      mostrarEstadoCategorias();

      mostrarMensaje(
        'mensajeInicio',
        'El proceso de la categoría "' +
          categoriaGuardada +
          '" quedó guardado. Puede continuar después.',
        'exito'
      );

      categoriaActual = '';

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }

    function finalizarInventario() {
      if (guardandoInventario) {
        return;
      }

      ocultarMensaje('mensajeInventario');

      const pendientes =
        productos.filter(function (producto) {
          return (
            producto.cerrado === '' ||
            producto.abierto === ''
          );
        }).length;

      if (pendientes > 0) {
        mostrarMensaje(
          'mensajeInventario',
          'Faltan ' +
          pendientes +
          ' productos por completar. ' +
          'Registre Cerrado y Abierto o utilice ' +
          '“Completar vacíos con 0”.',
          'error'
        );

        return;
      }

      const confirmar = window.confirm(
        '¿Confirma que desea finalizar la categoría ' +
        categoriaActual +
        ' de ' +
        puntoVentaActual +
        '?'
      );

      if (!confirmar) {
        return;
      }

      // Conserva el último valor digitado antes de iniciar el envío.
      guardarBorradorAhora();

      guardandoInventario = true;

      const boton =
        document.getElementById('botonFinalizar');

      const botonGuardarProceso =
        document.getElementById(
          'botonGuardarProceso'
        );

      boton.disabled = true;
      botonGuardarProceso.disabled = true;
      boton.textContent =
        'Finalizando...';

      const datos = {
        puntoVenta: puntoVentaActual,
        fecha: fechaActual,
        categoria: categoriaActual,

        conteos: productos.map(
          function (producto) {
            return {
              item: producto.item,
              producto: producto.producto,
              udm: producto.udm,
              cerrado: producto.cerrado,
              abierto: producto.abierto
            };
          }
        )
      };

      monthlyApi
        .withSuccessHandler(function (resultado) {
          eliminarBorrador();

          const estadoActual =
            estadosCategorias.find(estado =>
              estado.categoria === categoriaActual
            );

          if (estadoActual) {
            estadoActual.guardada = true;
          }

          actualizarCategoriaGuardadaEnSelector();
          mostrarEstadoCategorias();

          document
            .getElementById('mensajeExito')
            .textContent =
              'Inventario finalizado correctamente: ' +
              resultado.registros +
              ' productos registrados.';

          document
            .getElementById('pantallaInventario')
            .classList.add('oculto');

          document
            .getElementById('pantallaExito')
            .classList.remove('oculto');

          boton.disabled = false;
          botonGuardarProceso.disabled = false;
          boton.textContent =
            'Finalizar';
          guardandoInventario = false;
        })
        .withFailureHandler(function (error) {
          boton.disabled = false;
          botonGuardarProceso.disabled = false;
          boton.textContent =
            'Finalizar';
          guardandoInventario = false;

          mostrarMensaje(
            'mensajeInventario',
            obtenerMensajeError(error),
            'error'
          );

          window.scrollTo({
            top: 0,
            behavior: 'smooth'
          });
        })
        .guardarInventario(datos);
    }

    function actualizarCategoriaGuardadaEnSelector() {
      const selector = document.getElementById(
        'categoriaInventario'
      );

      Array.from(selector.options)
        .forEach(opcion => {
          if (opcion.value !== categoriaActual) {
            return;
          }

          opcion.disabled = true;
          opcion.textContent =
            categoriaActual + ' — Ya guardada';
        });
    }

    function volverMenuCategorias() {
      productos = [];

      document
        .getElementById('categoriaInventario')
        .value = '';

      document
        .getElementById('pantallaExito')
        .classList.add('oculto');

      document
        .getElementById('pantallaInicio')
        .classList.remove('oculto');

      mostrarEstadoCategorias();

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }

    function nuevoInventario() {
      productos = [];
      puntoVentaActual = '';
      fechaActual = '';
      categoriaActual = '';
      estadosCategorias = [];

      document
        .getElementById('puntoVenta')
        .value = '';

      const selectorCategoria =
        document
          .getElementById('categoriaInventario');

      selectorCategoria.innerHTML =
        '<option value="">' +
        'Seleccione primero el PDV' +
        '</option>';

      selectorCategoria.disabled = true;

      document
        .getElementById('controlCategorias')
        .classList.add('oculto');

      asignarFechaActual();

      document
        .getElementById('pantallaExito')
        .classList.add('oculto');

      document
        .getElementById('pantallaInicio')
        .classList.remove('oculto');

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }

    function guardarBorrador() {
      if (temporizadorBorrador) {
        clearTimeout(temporizadorBorrador);
      }

      // localStorage es síncrono. Se espera una pausa breve para no
      // convertir y escribir toda la lista con cada tecla digitada.
      temporizadorBorrador = setTimeout(
        function () {
          temporizadorBorrador = null;
          guardarBorradorAhora();
        },
        500
      );
    }

    function guardarBorradorAhora() {
      if (temporizadorBorrador) {
        clearTimeout(temporizadorBorrador);
        temporizadorBorrador = null;
      }

      try {
        localStorage.setItem(
          obtenerClaveBorrador(),

          JSON.stringify(
            productos.map(function (producto) {
              return {
                item: producto.item,
                cerrado: producto.cerrado,
                abierto: producto.abierto
              };
            })
          )
        );
        // Migrate older name-based keys only after the new draft is stored.
        clavesBorradorPara(puntoVentaActual, fechaActual, categoriaActual)
          .slice(1).forEach(clave => localStorage.removeItem(clave));
        return true;
      } catch (error) {
        console.log(
          'No se pudo guardar el borrador.'
        );
        return false;
      }
    }

    function recuperarBorrador() {
      try {
        const borrador = leerBorradorPara(
          puntoVentaActual, fechaActual, categoriaActual
        );

        const cantidades = {};

        borrador.forEach(function (registro) {
          cantidades[String(registro.item)] = {
            cerrado: registro.cerrado,
            abierto: registro.abierto
          };
        });

        productos.forEach(function (producto) {
          const clave = String(producto.item);

          if (
            Object.prototype.hasOwnProperty.call(
              cantidades,
              clave
            )
          ) {
            const conteo = cantidades[clave];

            producto.cerrado =
              conteo.cerrado === undefined
                ? ''
                : conteo.cerrado;

            producto.abierto =
              conteo.abierto === undefined
                ? ''
                : conteo.abierto;
          }
        });
      } catch (error) {
        console.log(
          'No se pudo recuperar el borrador.'
        );
      }
    }

    function eliminarBorrador() {
      if (temporizadorBorrador) {
        clearTimeout(temporizadorBorrador);
        temporizadorBorrador = null;
      }

      try {
        clavesBorradorPara(puntoVentaActual, fechaActual, categoriaActual)
          .forEach(clave => localStorage.removeItem(clave));
      } catch (error) {
        console.log(
          'No se pudo eliminar el borrador.'
        );
      }
    }

    function obtenerClaveBorrador() {
      return obtenerClaveBorradorPara(
        puntoVentaActual,
        fechaActual,
        categoriaActual
      );
    }

    function obtenerClaveBorradorPara(
      puntoVenta,
      fecha,
      categoria
    ) {
      return 'inventario-mensual-v2-' + JSON.stringify([
        normalizarTexto(puntoVenta), fecha, normalizarTexto(categoria)
      ]);
    }

    function clavesBorradorPara(puntoVenta, fecha, categoria) {
      const actual = obtenerClaveBorradorPara(puntoVenta, fecha, categoria);
      const anterior = 'inventario-mensual-v1-' + puntoVenta + '-' + fecha + '-' + categoria;
      const prefijo = 'inventario-mensual-v1-';
      const separador = '-' + fecha + '-';
      const equivalentes = Object.keys(localStorage).filter(clave => {
        if (!clave.startsWith(prefijo)) return false;
        const corte = clave.indexOf(separador, prefijo.length);
        return corte !== -1 &&
          normalizarTexto(clave.slice(prefijo.length, corte)) === normalizarTexto(puntoVenta) &&
          normalizarTexto(clave.slice(corte + separador.length)) === normalizarTexto(categoria);
      }).sort();
      return [actual, anterior, ...equivalentes.filter(clave => clave !== anterior)];
    }

    function leerBorradorPara(puntoVenta, fecha, categoria) {
      for (const clave of clavesBorradorPara(puntoVenta, fecha, categoria)) {
        const contenido = localStorage.getItem(clave);
        if (contenido === null) continue;
        const borrador = JSON.parse(contenido);
        return Array.isArray(borrador)
          ? borrador.filter(registro => registro && typeof registro === 'object')
          : [];
      }
      return [];
    }

    function mostrarMensaje(
      id,
      texto,
      tipo
    ) {
      const elemento =
        document.getElementById(id);

      elemento.textContent = texto;
      elemento.className =
        'mensaje ' + tipo;
    }

    function ocultarMensaje(id) {
      const elemento =
        document.getElementById(id);

      elemento.textContent = '';
      elemento.className = 'mensaje';
    }

    function obtenerMensajeError(error) {
      return error && error.message
        ? error.message
        : String(
            error ||
            'Ocurrió un error inesperado.'
          );
    }

    function formatearFecha(fecha) {
      const partes = fecha.split('-');

      if (partes.length !== 3) {
        return fecha;
      }

      return (
        partes[2] +
        '/' +
        partes[1] +
        '/' +
        partes[0]
      );
    }

    function normalizarTexto(texto) {
      return String(texto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, ' ')
        .toLowerCase()
        .trim();
    }

    function escaparHTML(valor) {
      return String(valor ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }
