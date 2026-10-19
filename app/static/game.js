let datosActuales = { nombre: null, sala: null };
let ultimaClave = "";
let problema = "";
let temporizador = null;
let consultando = false;
let enviando = false;
let cartelCerrado = "";
let estadoPartidaAnterior = "";

function el(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

async function api(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    throw new Error(datos.error || "No se pudo completar la acción");
  }
  return datos;
}

function aplicar(datos) {
  const estadoNuevo = datos.sala ? datos.sala.estado : "";
  const acabaDeTerminar =
    (estadoNuevo === "ganada" || estadoNuevo === "empate")
    && estadoNuevo !== estadoPartidaAnterior;

  // Si la partida acaba de terminar, el cartel debe volver a salir
  // aunque en una revancha anterior se hubiera cerrado.
  if (acabaDeTerminar) {
    cartelCerrado = "";
  }
  estadoPartidaAnterior = estadoNuevo;

  datosActuales = datos;
  const clave = JSON.stringify(datos);
  sincronizarPoll();
  if (clave === ultimaClave && !acabaDeTerminar) return;
  ultimaClave = clave;
  problema = "";
  render();
}

function mostrarProblema(texto) {
  if (problema === texto) return;
  problema = texto;
  render();
}

function sincronizarPoll() {
  const enSala = Boolean(datosActuales.sala);
  if (enSala && !temporizador) {
    temporizador = setInterval(consultar, 500);
  }
  if (!enSala && temporizador) {
    clearInterval(temporizador);
    temporizador = null;
  }
}

async function consultar() {
  if (consultando) return;
  consultando = true;
  try {
    aplicar(await api("/api/estado"));
  } catch (error) {
    mostrarProblema("Sin conexión con el servidor. Reintentando...");
  } finally {
    consultando = false;
  }
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && datosActuales.sala) {
    consultar();
  }
});

window.addEventListener("focus", () => {
  if (datosActuales.sala) consultar();
});

async function accion(ruta, payload) {
  if (enviando) return;
  enviando = true;
  problema = "";
  try {
    aplicar(await api(ruta, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }));
  } catch (error) {
    mostrarProblema(error.message);
  } finally {
    enviando = false;
  }
}

function claveResultado(sala) {
  if (!sala || (sala.estado !== "ganada" && sala.estado !== "empate")) return "";
  const quien = sala.ganador ? sala.ganador.slot : "empate";
  const ultima = sala.ultimaJugada
    ? `${sala.ultimaJugada.fila}-${sala.ultimaJugada.columna}`
    : "x";
  return `${sala.codigo}:${sala.estado}:${quien}:${ultima}`;
}

function textoCartel(sala) {
  if (sala.estado === "empate") {
    return {
      clase: "empate",
      titulo: "Empate",
      detalle: "El tablero se llenó sin cuatro en línea.",
    };
  }
  const gane = sala.ganador && sala.tu && sala.ganador.slot === sala.tu.slot;
  if (gane) {
    return {
      clase: "victoria",
      titulo: "¡Ganaste!",
      detalle: "Cuatro en línea. Bien jugado.",
    };
  }
  return {
    clase: "derrota",
    titulo: "Perdiste",
    detalle: `Ganó ${sala.ganador.nombre}.`,
  };
}

function cartelResultado(sala) {
  const clave = claveResultado(sala);
  if (!clave || clave === cartelCerrado) return null;

  const texto = textoCartel(sala);
  const fondo = el("div", `cartel-fondo ${texto.clase}`);
  fondo.setAttribute("role", "dialog");
  fondo.setAttribute("aria-modal", "true");
  fondo.setAttribute("aria-label", texto.titulo);

  const caja = el("div", "cartel");
  caja.append(el("p", "cartel-titulo", texto.titulo));
  caja.append(el("p", "cartel-detalle", texto.detalle));

  const acciones = el("div", "cartel-acciones");
  const otra = el("button", "principal", "Jugar otra vez");
  otra.type = "button";
  otra.onclick = () => {
    cartelCerrado = clave;
    accion("/api/revancha");
  };
  const cerrar = el("button", "secundario", "Cerrar");
  cerrar.type = "button";
  cerrar.onclick = () => {
    cartelCerrado = clave;
    render();
  };
  acciones.append(otra, cerrar);
  caja.append(acciones);
  fondo.append(caja);
  fondo.addEventListener("click", (evento) => {
    if (evento.target === fondo) {
      cartelCerrado = clave;
      render();
    }
  });
  return fondo;
}

function quitarCartelDom() {
  document.querySelectorAll(".cartel-fondo").forEach((nodo) => nodo.remove());
}

function render() {
  const panel = el("section", "panel");
  panel.append(cabecera());
  if (!datosActuales.nombre) panel.append(pantallaNombre());
  else if (!datosActuales.sala) panel.append(pantallaSala());
  else panel.append(pantallaJuego());
  if (problema) panel.append(el("p", "problema", problema));
  document.querySelector("#app").replaceChildren(panel);

  // El cartel va en body para que no lo tape el panel ni lo borre el poll.
  quitarCartelDom();
  if (datosActuales.sala) {
    const cartel = cartelResultado(datosActuales.sala);
    if (cartel) document.body.append(cartel);
  }
}

function cabecera() {
  const header = el("header", "cabecera");
  header.append(el("h1", null, "Conecta 4"));
  header.append(el("p", "ayuda", "Dos jugadores. Cada navegador tiene su propia sesión."));
  return header;
}

function pantallaNombre() {
  const form = document.createElement("form");
  const input = document.createElement("input");
  input.placeholder = "Tu nombre";
  input.maxLength = 20;
  input.required = true;
  input.autocomplete = "name";
  const boton = el("button", "principal", "Continuar");
  boton.type = "submit";
  form.append(input, boton);
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    accion("/api/nombre", { nombre: input.value });
  });
  return form;
}

function pantallaSala() {
  const caja = el("div");
  const crear = el("button", "principal", "Crear sala");
  crear.type = "button";
  crear.onclick = () => accion("/api/salas");
  caja.append(crear);

  const separador = el("div", "separador");
  separador.append(el("span", null, "o"));
  caja.append(separador);

  const form = document.createElement("form");
  const input = document.createElement("input");
  input.className = "codigo-input";
  input.placeholder = "CÓDIGO";
  input.maxLength = 4;
  input.required = true;
  const boton = el("button", "secundario", "Unirse");
  boton.type = "submit";
  form.append(input, boton);
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    accion("/api/salas/unirse", { codigo: input.value.trim().toUpperCase() });
  });
  caja.append(form);
  caja.append(el(
    "p",
    "pista",
    "El otro jugador tiene que abrir esta página en una ventana de incógnito o en otro navegador. En la misma ventana compartirían tu sesión."
  ));
  return caja;
}

function pantallaJuego() {
  const sala = datosActuales.sala;
  const caja = el("div");
  const marcador = el("div", "marcador");
  marcador.append(tarjetaJugador(sala.tu, sala.tuTurno));
  marcador.append(el("span", "contra", "vs"));
  const turnoRival = sala.rival && sala.turno === sala.rival.slot && sala.estado === "jugando";
  marcador.append(tarjetaJugador(sala.rival, turnoRival));
  caja.append(marcador);
  caja.append(el("p", "estado-turno", textoTurno(sala)));

  if (sala.estado === "esperando") {
    caja.append(el("p", "codigo", sala.codigo));
    const copiar = el("button", "secundario", "Copiar código");
    copiar.type = "button";
    copiar.onclick = async () => {
      try {
        await navigator.clipboard.writeText(sala.codigo);
        copiar.textContent = "Código copiado";
      } catch (error) {
        copiar.textContent = sala.codigo;
      }
    };
    caja.append(copiar);
    caja.append(el(
      "p",
      "pista",
      "Pásale este código. La otra persona entra desde una ventana de incógnito, escribe su nombre y pulsa Unirse."
    ));
  }

  caja.append(tablero(sala));

  const acciones = el("div", "acciones");
  if (sala.estado === "ganada" || sala.estado === "empate") {
    const otra = el("button", "principal", "Jugar otra vez");
    otra.type = "button";
    otra.onclick = () => accion("/api/revancha");
    acciones.append(otra);
  }
  const salir = el("button", "secundario", "Salir de la sala");
  salir.type = "button";
  salir.onclick = () => accion("/api/salir");
  acciones.append(salir);
  caja.append(acciones);
  return caja;
}

function textoTurno(sala) {
  if (sala.estado === "esperando") return "Esperando al segundo jugador";
  if (sala.estado === "empate") return "Empate. El tablero se llenó sin cuatro en línea.";
  if (sala.estado === "ganada") {
    const gane = sala.ganador && sala.tu && sala.ganador.slot === sala.tu.slot;
    return gane ? "Ganaste. Cuatro en línea." : `Ganó ${sala.ganador.nombre}.`;
  }
  return sala.tuTurno ? "Tu turno. Elige una columna." : `Turno de ${sala.rival.nombre}.`;
}

function tarjetaJugador(jugador, activo) {
  const caja = el("div", activo ? "jugador activo" : "jugador");
  caja.append(el("span", `punto ${jugador ? jugador.color : "vacio"}`));
  const texto = el("div");
  texto.append(el("strong", null, jugador ? jugador.nombre : "Esperando..."));
  if (jugador) texto.append(document.createTextNode(" "));
  if (jugador) texto.append(el("span", "rol", jugador.color));
  caja.append(texto);
  return caja;
}

function tablero(sala) {
  const mesa = el("div", "tablero");
  const ganadoras = new Set((sala.lineaGanadora || []).map(([fila, columna]) => `${fila}-${columna}`));
  sala.tablero.forEach((fila, indiceFila) => {
    fila.forEach((valor, indiceColumna) => {
      let boton = mesa.children[indiceColumna];
      if (!boton) {
        boton = document.createElement("button");
        boton.type = "button";
        boton.className = "columna";
        boton.disabled = !sala.tuTurno;
        boton.setAttribute("aria-label", `Columna ${indiceColumna + 1}`);
        boton.onclick = () => accion("/api/jugada", { columna: indiceColumna + 1 });
        boton.addEventListener("mouseenter", () => mostrarVistaPrevia(boton, indiceColumna));
        boton.addEventListener("mouseleave", () => quitarVistaPrevia(boton));
        mesa.append(boton);
      }
      const celda = el("span", "celda");
      if (valor) {
        const clases = ["ficha", valor === 1 ? "rojo" : "amarillo"];
        const ultima = sala.ultimaJugada;
        if (ultima && ultima.fila === indiceFila && ultima.columna === indiceColumna) {
          clases.push("cayendo");
        }
        if (ganadoras.has(`${indiceFila}-${indiceColumna}`)) clases.push("gana");
        const ficha = el("span", clases.join(" "));
        if (clases.includes("cayendo")) {
          ficha.style.setProperty("--desde", `${(indiceFila + 1) * 72}px`);
        }
        celda.append(ficha);
      }
      boton.append(celda);
    });
  });
  sala.tablero[0].forEach((_, indiceColumna) => {
    mesa.children[indiceColumna].append(el("span", "numero", String(indiceColumna + 1)));
  });
  return mesa;
}

// Solo pinta un avance. La columna real la vuelve a calcular el servidor.
function mostrarVistaPrevia(boton, indiceColumna) {
  const sala = datosActuales.sala;
  if (!sala || !sala.tuTurno) return;
  const fila = filaLibre(sala.tablero, indiceColumna);
  if (fila < 0) return;
  const celdas = boton.querySelectorAll(".celda");
  if (celdas[fila].querySelector(".ficha")) return;
  celdas[fila].append(el("span", `ficha preview ${sala.tu.color}`));
}

function quitarVistaPrevia(boton) {
  boton.querySelectorAll(".preview").forEach((nodo) => nodo.remove());
}

function filaLibre(tablero, columna) {
  for (let fila = tablero.length - 1; fila >= 0; fila -= 1) {
    if (tablero[fila][columna] === 0) return fila;
  }
  return -1;
}

consultar();
