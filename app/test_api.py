import logging
import unittest

import app as servidor


class TestApi(unittest.TestCase):
    def setUp(self):
        servidor.SALAS.clear()
        servidor.logger.handlers.clear()
        servidor.logger.addHandler(logging.NullHandler())
        self.ana = servidor.app.test_client()
        self.luis = servidor.app.test_client()

    def test_dos_sesiones_juegan_y_ana_gana(self):
        self.assertEqual(self.ana.get("/").status_code, 200)
        self.assertIn("Conecta 4", self.ana.get("/").get_data(as_text=True))

        self.ana.post("/api/nombre", json={"nombre": "Ana"})
        creada = self.ana.post("/api/salas").get_json()
        codigo = creada["sala"]["codigo"]
        self.assertEqual(creada["sala"]["tu"]["color"], "rojo")
        self.assertEqual(creada["sala"]["estado"], "esperando")

        self.luis.post("/api/nombre", json={"nombre": "Luis"})
        unido = self.luis.post("/api/salas/unirse", json={"codigo": codigo.lower()}).get_json()
        self.assertEqual(unido["sala"]["tu"]["slot"], 2)
        self.assertEqual(unido["sala"]["estado"], "jugando")
        self.assertFalse(unido["sala"]["tuTurno"])

        rechazada = self.luis.post("/api/jugada", json={"columna": 7})
        self.assertEqual(rechazada.status_code, 409)

        for columna in (1, 2, 3):
            self.assertEqual(self.ana.post("/api/jugada", json={"columna": columna}).status_code, 200)
            self.assertEqual(self.luis.post("/api/jugada", json={"columna": 7}).status_code, 200)

        final = self.ana.post("/api/jugada", json={"columna": 4}).get_json()
        self.assertEqual(final["sala"]["estado"], "ganada")
        self.assertEqual(final["sala"]["ganador"]["nombre"], "Ana")
        self.assertGreaterEqual(len(final["sala"]["lineaGanadora"]), 4)

        luis = self.luis.get("/api/estado").get_json()
        self.assertEqual(luis["sala"]["ganador"]["nombre"], "Ana")
        self.assertEqual(luis["nombre"], "Luis")
        self.assertEqual(self.ana.get("/api/estado").get_json()["nombre"], "Ana")

    def test_la_misma_sesion_no_ocupa_los_dos_lados(self):
        self.ana.post("/api/nombre", json={"nombre": "Ana"})
        codigo = self.ana.post("/api/salas").get_json()["sala"]["codigo"]
        otra_vez = self.ana.post("/api/salas/unirse", json={"codigo": codigo}).get_json()
        self.assertEqual(otra_vez["sala"]["tu"]["slot"], 1)
        self.assertIsNone(otra_vez["sala"]["rival"])

    def test_un_tercero_no_entra_y_el_codigo_malo_falla(self):
        self.ana.post("/api/nombre", json={"nombre": "Ana"})
        self.luis.post("/api/nombre", json={"nombre": "Luis"})
        codigo = self.ana.post("/api/salas").get_json()["sala"]["codigo"]
        self.luis.post("/api/salas/unirse", json={"codigo": codigo})
        tercero = servidor.app.test_client()
        tercero.post("/api/nombre", json={"nombre": "Sol"})
        self.assertEqual(tercero.post("/api/salas/unirse", json={"codigo": codigo}).status_code, 409)
        self.assertEqual(self.ana.post("/api/salas/unirse", json={"codigo": "ZZZZ"}).status_code, 404)

    def test_columna_llena_revancha_y_salir(self):
        self.ana.post("/api/nombre", json={"nombre": "Ana"})
        self.luis.post("/api/nombre", json={"nombre": "Luis"})
        codigo = self.ana.post("/api/salas").get_json()["sala"]["codigo"]
        self.luis.post("/api/salas/unirse", json={"codigo": codigo})
        for _ in range(3):
            self.ana.post("/api/jugada", json={"columna": 1})
            self.luis.post("/api/jugada", json={"columna": 1})
        llena = self.ana.post("/api/jugada", json={"columna": 1})
        self.assertEqual(llena.status_code, 409)

        for columna in (2, 3, 4):
            self.ana.post("/api/jugada", json={"columna": columna})
            if columna != 4:
                self.luis.post("/api/jugada", json={"columna": 7})
        self.assertEqual(self.ana.get("/api/estado").get_json()["sala"]["estado"], "ganada")

        revancha = self.luis.post("/api/revancha").get_json()
        self.assertEqual(revancha["sala"]["estado"], "jugando")
        for fila in revancha["sala"]["tablero"]:
            self.assertEqual(fila, [0, 0, 0, 0, 0, 0, 0])
        self.assertTrue(self.ana.get("/api/estado").get_json()["sala"]["tuTurno"])

        fuera = self.ana.post("/api/salir").get_json()
        self.assertIsNone(fuera["sala"])


if __name__ == "__main__":
    unittest.main()
