"""Servidor web de Conecta 4.

Hace tres cosas:
1. Recuerda quién es cada navegador con una cookie de sesión.
2. Recibe las jugadas y les aplica las reglas.
3. Escribe un evento JSON cada vez que pasa algo importante en la partida.
"""

import json
import logging
import os
import random
import sys
import threading
import uuid

from flask import Flask, jsonify, render_template, request, session

from game import ErrorDeJuego, Sala

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
logger = logging.getLogger("conecta4")
SALAS = {}
candado = threading.Lock()


class FormatoJson(logging.Formatter):
    """Convierte cada evento en una sola línea JSON para Loki."""

    RESERVADOS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "taskName", "task",
    }

    def format(self, record):
        datos = {"message": record.getMessage(), "level": record.levelname}
        for clave, valor in record.__dict__.items():
            if clave not in self.RESERVADOS and not clave.startswith("_"):
                datos[clave] = valor
        return json.dumps(datos, ensure_ascii=False)


def configurar_logs():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(FormatoJson())
    logger.addHandler(consola)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def agregar_archivo_de_logs():
    """Promtail lee este archivo. La consola sigue mostrando lo mismo."""
    ruta = os.environ.get("LOG_PATH", "")
    if not ruta:
        return
    if any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        return
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    archivo = logging.FileHandler(ruta, encoding="utf-8")
    archivo.setFormatter(FormatoJson())
    logger.addHandler(archivo)


def log_event(event, message, **campos):
    logger.info(message, extra={"event": event, **campos})


def crear_aplicacion():
    configurar_logs()
    aplicacion = Flask(__name__)
    aplicacion.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "conecta4-examen"),
        SESSION_COOKIE_NAME="conecta4",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        JSON_AS_ASCII=False,
    )
    aplicacion.json.ensure_ascii = False
    registrar_rutas(aplicacion)
    return aplicacion


def asegurar_jugador():
    if not session.get("jugador_id"):
        session["jugador_id"] = uuid.uuid4().hex
    return session["jugador_id"]


def jugador_actual():
    return {"id": session["jugador_id"], "nombre": session["nombre"]}


def normalizar_nombre(texto):
    if not isinstance(texto, str):
        raise ErrorDeJuego("Escribe tu nombre")
    nombre = " ".join(texto.split())
    if not nombre or len(nombre) > 20:
        raise ErrorDeJuego("El nombre debe tener entre 1 y 20 caracteres")
    return nombre


def nuevo_codigo():
    for _ in range(20):
        codigo = "".join(random.choice(ALFABETO) for _ in range(4))
        if codigo not in SALAS:
            return codigo
    raise ErrorDeJuego("No se pudo crear un código de sala")


def construir_respuesta():
    jugador_id = asegurar_jugador()
    codigo = session.get("sala")
    sala = SALAS.get(codigo) if codigo else None
    if sala is None:
        if codigo:
            session.pop("sala", None)
        vista = None
    else:
        try:
            vista = sala.estado_para(jugador_id)
        except ErrorDeJuego:
            session.pop("sala", None)
            vista = None
    return {"nombre": session.get("nombre"), "sala": vista}


def error(mensaje, codigo):
    return jsonify({"error": mensaje}), codigo


def registrar_rutas(aplicacion):
    @aplicacion.after_request
    def sin_cache(respuesta):
        # Evita que el navegador se quede con un JS o un estado viejos.
        if request.path.startswith("/api/") or request.path.startswith("/static/") or request.path == "/":
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    @aplicacion.get("/")
    def inicio():
        return render_template("index.html")

    @aplicacion.get("/api/salud")
    def salud():
        return jsonify({"ok": True})

    @aplicacion.get("/api/estado")
    def estado():
        with candado:
            return jsonify(construir_respuesta())

    @aplicacion.post("/api/nombre")
    def poner_nombre():
        cuerpo = request.get_json(silent=True) or {}
        try:
            nombre = normalizar_nombre(cuerpo.get("nombre"))
        except ErrorDeJuego as exc:
            return error(str(exc), 400)
        with candado:
            asegurar_jugador()
            session["nombre"] = nombre
            return jsonify(construir_respuesta())

    @aplicacion.post("/api/salas")
    def crear_sala():
        with candado:
            if not session.get("nombre"):
                return error("Primero escribe tu nombre", 400)
            asegurar_jugador()
            if session.get("sala") in SALAS:
                return jsonify(construir_respuesta())
            codigo = nuevo_codigo()
            SALAS[codigo] = Sala(codigo, jugador_actual())
            session["sala"] = codigo
            log_event(
                "partida_creada",
                f"{session['nombre']} creó la sala {codigo}",
                sala=codigo,
                jugador=session["nombre"],
            )
            return jsonify(construir_respuesta())

    @aplicacion.post("/api/salas/unirse")
    def unirse():
        cuerpo = request.get_json(silent=True) or {}
        codigo = str(cuerpo.get("codigo", "")).strip().upper()
        with candado:
            if not session.get("nombre"):
                return error("Primero escribe tu nombre", 400)
            sala = SALAS.get(codigo)
            if sala is None:
                return error("No existe una sala con ese código", 404)
            asegurar_jugador()
            ya_estaba = any(
                jugador and jugador["id"] == session["jugador_id"]
                for jugador in sala.jugadores.values()
            )
            try:
                sala.unirse(jugador_actual())
            except ErrorDeJuego as exc:
                return error(str(exc), 409)
            session["sala"] = codigo
            if not ya_estaba:
                log_event(
                    "partida_iniciada",
                    f"{session['nombre']} entró a la sala {codigo}. Empieza la partida",
                    sala=codigo,
                    jugador=session["nombre"],
                )
            return jsonify(construir_respuesta())

    @aplicacion.post("/api/jugada")
    def jugada():
        cuerpo = request.get_json(silent=True) or {}
        columna = cuerpo.get("columna")
        if isinstance(columna, bool) or not isinstance(columna, int):
            return error("La columna debe ser un número del 1 al 7", 400)
        with candado:
            if not session.get("nombre"):
                return error("Primero escribe tu nombre", 400)
            codigo = session.get("sala")
            sala = SALAS.get(codigo) if codigo else None
            if sala is None:
                return error("No estás en una sala", 400)
            asegurar_jugador()
            try:
                sala.jugar(session["jugador_id"], columna)
            except ErrorDeJuego as exc:
                log_event(
                    "jugada_invalida",
                    f"Jugada rechazada: {exc}",
                    sala=codigo,
                    jugador=session["nombre"],
                    columna=columna,
                    motivo=str(exc),
                )
                return error(str(exc), 409)
            log_event(
                "jugada",
                f"{session['nombre']} soltó una ficha en la columna {columna}",
                sala=codigo,
                jugador=session["nombre"],
                columna=columna,
            )
            if sala.estado == "ganada":
                ganador = sala.ganador
                color = "rojo" if sala.slot_de(ganador["id"]) == 1 else "amarillo"
                log_event(
                    "victoria",
                    f"Ganó {ganador['nombre']} ({color})",
                    sala=codigo,
                    jugador=ganador["nombre"],
                    color=color,
                )
            elif sala.estado == "empate":
                log_event("empate", f"Empate en la sala {codigo}", sala=codigo)
            return jsonify(construir_respuesta())

    @aplicacion.post("/api/revancha")
    def revancha():
        with candado:
            codigo = session.get("sala")
            sala = SALAS.get(codigo) if codigo else None
            if sala is None:
                return error("No estás en una sala", 400)
            try:
                sala.revancha()
            except ErrorDeJuego as exc:
                return error(str(exc), 409)
            log_event(
                "revancha",
                f"Nueva partida en la sala {codigo}",
                sala=codigo,
                jugador=session.get("nombre"),
            )
            return jsonify(construir_respuesta())

    @aplicacion.post("/api/salir")
    def salir():
        with candado:
            session.pop("sala", None)
            return jsonify(construir_respuesta())


app = crear_aplicacion()


def main():
    agregar_archivo_de_logs()
    puerto = int(os.environ.get("PORT", "8080"))
    log_event("servidor", "Servidor de Conecta 4 listo", puerto=puerto)
    app.run(host="0.0.0.0", port=puerto, threaded=True)


if __name__ == "__main__":
    main()
