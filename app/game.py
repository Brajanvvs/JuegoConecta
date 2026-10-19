"""Reglas de Conecta 4.

El tablero tiene 6 filas y 7 columnas. La fila 0 es la de arriba
en la pantalla. Una ficha siempre cae a la fila libre más baja.
"""

FILAS = 6
COLUMNAS = 7
VACIO = 0


class ErrorDeJuego(Exception):
    """Una jugada que el servidor no puede aceptar."""


def tablero_vacio():
    return [[VACIO for _ in range(COLUMNAS)] for _ in range(FILAS)]


def soltar_ficha(tablero, columna, jugador):
    """Coloca la ficha y devuelve la fila donde quedó."""
    for fila in range(FILAS - 1, -1, -1):
        if tablero[fila][columna] == VACIO:
            tablero[fila][columna] = jugador
            return fila
    raise ErrorDeJuego("Esa columna está llena")


def linea_ganadora(tablero, fila, columna, jugador):
    """Busca cuatro o más fichas seguidas que pasen por esta casilla."""
    direcciones = ((0, 1), (1, 0), (1, 1), (1, -1))
    for avance_fila, avance_columna in direcciones:
        linea = [[fila, columna]]
        linea += _seguir(tablero, fila, columna, avance_fila, avance_columna, jugador)
        linea += _seguir(tablero, fila, columna, -avance_fila, -avance_columna, jugador)
        if len(linea) >= 4:
            return linea
    return None


def _seguir(tablero, fila, columna, avance_fila, avance_columna, jugador):
    celdas = []
    fila += avance_fila
    columna += avance_columna
    while (
        0 <= fila < FILAS
        and 0 <= columna < COLUMNAS
        and tablero[fila][columna] == jugador
    ):
        celdas.append([fila, columna])
        fila += avance_fila
        columna += avance_columna
    return celdas


def tablero_lleno(tablero):
    return all(celda != VACIO for celda in tablero[0])


class Sala:
    """Una partida entre dos jugadores identificados por su sesión."""

    def __init__(self, codigo, jugador):
        self.codigo = codigo
        self.tablero = tablero_vacio()
        self.jugadores = {1: jugador, 2: None}
        self.turno = 1
        self.estado = "esperando"
        self.ganador = None
        self.linea = []
        self.ultima = None

    def unirse(self, jugador):
        for existente in self.jugadores.values():
            if existente and existente["id"] == jugador["id"]:
                return
        if self.jugadores[2] is not None:
            raise ErrorDeJuego("La sala ya tiene dos jugadores")
        self.jugadores[2] = jugador
        self.estado = "jugando"

    def jugar(self, jugador_id, columna):
        if self.estado == "esperando":
            raise ErrorDeJuego("Todavía falta el otro jugador")
        if self.estado in ("ganada", "empate"):
            raise ErrorDeJuego("La partida ya terminó")
        slot = self.slot_de(jugador_id)
        if slot != self.turno:
            raise ErrorDeJuego("No es tu turno")
        if isinstance(columna, bool) or not isinstance(columna, int) or not 1 <= columna <= COLUMNAS:
            raise ErrorDeJuego("Elige una columna del 1 al 7")

        fila = soltar_ficha(self.tablero, columna - 1, slot)
        self.ultima = {"fila": fila, "columna": columna - 1}
        linea = linea_ganadora(self.tablero, fila, columna - 1, slot)
        if linea:
            self.estado = "ganada"
            self.ganador = self.jugadores[slot]
            self.linea = linea
        elif tablero_lleno(self.tablero):
            self.estado = "empate"
            self.linea = []
        else:
            self.turno = 2 if slot == 1 else 1
        return self.estado

    def revancha(self):
        if self.jugadores[2] is None:
            raise ErrorDeJuego("Falta el segundo jugador")
        if self.estado not in ("ganada", "empate"):
            raise ErrorDeJuego("La partida todavía no termina")
        self.tablero = tablero_vacio()
        self.turno = 1
        self.estado = "jugando"
        self.ganador = None
        self.linea = []
        self.ultima = None

    def slot_de(self, jugador_id):
        for slot, jugador in self.jugadores.items():
            if jugador and jugador["id"] == jugador_id:
                return slot
        raise ErrorDeJuego("No estás en esta sala")

    def estado_para(self, jugador_id):
        tu_slot = self.slot_de(jugador_id)
        rival = self.jugadores[2 if tu_slot == 1 else 1]
        return {
            "codigo": self.codigo,
            "tablero": [fila[:] for fila in self.tablero],
            "turno": self.turno,
            "tuTurno": self.estado == "jugando" and self.turno == tu_slot,
            "estado": self.estado,
            "tu": self._publico(self.jugadores[tu_slot]),
            "rival": self._publico(rival) if rival else None,
            "ganador": self._publico(self.ganador) if self.ganador else None,
            "lineaGanadora": [celda[:] for celda in self.linea],
            "ultimaJugada": dict(self.ultima) if self.ultima else None,
        }

    def _publico(self, jugador):
        slot = self.slot_de(jugador["id"])
        return {
            "slot": slot,
            "nombre": jugador["nombre"],
            "color": "rojo" if slot == 1 else "amarillo",
        }
