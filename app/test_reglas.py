import unittest

from game import (
    COLUMNAS,
    FILAS,
    ErrorDeJuego,
    Sala,
    linea_ganadora,
    soltar_ficha,
    tablero_lleno,
    tablero_vacio,
)


class TestReglas(unittest.TestCase):
    def test_la_ficha_cae_al_fondo_y_se_apila(self):
        tablero = tablero_vacio()
        self.assertEqual(soltar_ficha(tablero, 3, 1), FILAS - 1)
        self.assertEqual(soltar_ficha(tablero, 3, 2), FILAS - 2)
        self.assertEqual(tablero[5][3], 1)
        self.assertEqual(tablero[4][3], 2)

    def test_columna_llena(self):
        tablero = tablero_vacio()
        for _ in range(FILAS):
            soltar_ficha(tablero, 0, 1)
        with self.assertRaises(ErrorDeJuego):
            soltar_ficha(tablero, 0, 2)

    def test_victoria_horizontal(self):
        tablero = tablero_vacio()
        for columna in range(4):
            fila = soltar_ficha(tablero, columna, 1)
        self.assertIsNotNone(linea_ganadora(tablero, fila, 3, 1))
        tablero_corto = tablero_vacio()
        for columna in range(3):
            fila = soltar_ficha(tablero_corto, columna, 1)
        self.assertIsNone(linea_ganadora(tablero_corto, fila, 2, 1))

    def test_victoria_vertical(self):
        tablero = tablero_vacio()
        fila = 0
        for _ in range(4):
            fila = soltar_ficha(tablero, 0, 1)
        self.assertIsNotNone(linea_ganadora(tablero, fila, 0, 1))

    def test_victoria_diagonal(self):
        tablero = tablero_vacio()
        soltar_ficha(tablero, 0, 2)
        soltar_ficha(tablero, 0, 2)
        soltar_ficha(tablero, 0, 2)
        soltar_ficha(tablero, 1, 2)
        soltar_ficha(tablero, 1, 2)
        soltar_ficha(tablero, 2, 2)
        soltar_ficha(tablero, 3, 1)
        soltar_ficha(tablero, 2, 1)
        soltar_ficha(tablero, 1, 1)
        fila = soltar_ficha(tablero, 0, 1)
        self.assertIsNotNone(linea_ganadora(tablero, fila, 0, 1))

    def test_victoria_diagonal_inversa(self):
        tablero = tablero_vacio()
        soltar_ficha(tablero, 1, 2)
        soltar_ficha(tablero, 2, 2)
        soltar_ficha(tablero, 2, 2)
        soltar_ficha(tablero, 3, 2)
        soltar_ficha(tablero, 3, 2)
        soltar_ficha(tablero, 3, 2)
        soltar_ficha(tablero, 0, 1)
        soltar_ficha(tablero, 1, 1)
        soltar_ficha(tablero, 2, 1)
        fila = soltar_ficha(tablero, 3, 1)
        self.assertIsNotNone(linea_ganadora(tablero, fila, 3, 1))

    def test_empate_cuando_el_tablero_se_llena_sin_cuatro_en_linea(self):
        patron = [
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
            [1, 1, 2, 2, 1, 1, 2],
            [2, 2, 1, 1, 2, 2, 1],
        ]
        sala = Sala("EMPT", {"id": "a", "nombre": "Ana"})
        sala.unirse({"id": "b", "nombre": "Luis"})
        sala.tablero = [fila[:] for fila in patron]
        sala.tablero[0][0] = 0
        sala.estado = "jugando"
        sala.turno = 1
        for fila in range(FILAS):
            for columna in range(COLUMNAS):
                jugador = sala.tablero[fila][columna]
                if jugador:
                    self.assertIsNone(linea_ganadora(sala.tablero, fila, columna, jugador))
        sala.jugar("a", 1)
        self.assertEqual(sala.estado, "empate")
        self.assertTrue(tablero_lleno(sala.tablero))

    def test_no_se_juega_fuera_de_turno_ni_en_columna_invalida(self):
        sala = Sala("AB12", {"id": "a", "nombre": "Ana"})
        sala.unirse({"id": "b", "nombre": "Luis"})
        with self.assertRaises(ErrorDeJuego):
            sala.jugar("b", 1)
        with self.assertRaises(ErrorDeJuego):
            sala.jugar("a", 8)
        sala.jugar("a", 1)
        self.assertEqual(sala.turno, 2)


if __name__ == "__main__":
    unittest.main()
