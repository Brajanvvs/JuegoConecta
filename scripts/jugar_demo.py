"""Juega una partida contra el servidor ya encendido, con dos sesiones distintas.

Sirve para probar el juego y para llenar los logs que después se ven en Grafana.
Uso: py scripts/jugar_demo.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8080"


class Cliente:
    def __init__(self, nombre):
        self.nombre = nombre
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def llamar(self, ruta, payload=None):
        datos = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            BASE + ruta,
            data=datos,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(req, timeout=5) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as exc:
            cuerpo = exc.read().decode()
            try:
                return exc.code, json.loads(cuerpo)
            except json.JSONDecodeError:
                return exc.code, {"error": cuerpo}
        except urllib.error.URLError as exc:
            return 0, {"error": str(exc.reason)}


def exigir(condicion, mensaje):
    if not condicion:
        print(mensaje)
        sys.exit(1)


def esperar_servidor():
    sonda = Cliente("salud")
    for _ in range(20):
        codigo, _ = sonda.llamar("/api/salud")
        if codigo == 200:
            return
        time.sleep(0.5)
    print("El servidor no responde en http://127.0.0.1:8080")
    sys.exit(1)


def main():
    esperar_servidor()
    ana = Cliente("Ana")
    luis = Cliente("Luis")

    ana.llamar("/api/nombre", {"nombre": "Ana"})
    _, creada = ana.llamar("/api/salas", {})
    codigo = creada["sala"]["codigo"]
    print(f"Ana creó la sala {codigo}")

    luis.llamar("/api/nombre", {"nombre": "Luis"})
    estado, pronto = luis.llamar("/api/jugada", {"columna": 1})
    exigir(estado == 400, f"Luis no debería poder jugar fuera de una sala: {pronto}")

    _, unido = luis.llamar("/api/salas/unirse", {"codigo": codigo})
    exigir(unido["sala"]["tu"]["slot"] == 2, "Luis no entró como segundo jugador")
    print("Luis entró desde otra sesión")

    estado, rechazada = luis.llamar("/api/jugada", {"columna": 7})
    exigir(estado == 409, f"La jugada fuera de turno debía rechazarse: {rechazada}")
    print(f"Jugada rechazada: {rechazada['error']}")

    for columna in (1, 2, 3):
        ana.llamar("/api/jugada", {"columna": columna})
        luis.llamar("/api/jugada", {"columna": 7})
    _, final = ana.llamar("/api/jugada", {"columna": 4})
    exigir(final["sala"]["estado"] == "ganada", f"Ana debía ganar: {final}")
    exigir(final["sala"]["ganador"]["nombre"] == "Ana", "El ganador debía ser Ana")
    print("Ana ganó con cuatro en línea en las columnas 1, 2, 3 y 4")

    _, revancha = luis.llamar("/api/revancha", {})
    exigir(revancha["sala"]["estado"] == "jugando", "La revancha no reinició la partida")
    print("Revancha lista. Ana vuelve a empezar.")


if __name__ == "__main__":
    main()
