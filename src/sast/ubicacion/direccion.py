# Vendorizado de ~/Claude_code/Analisis_siniestralidad/src/ubicacion/direccion.py (commit d057993, 2026-10-06).
# Solo se cambian las importaciones; la lógica es la del original.
"""Lectura de la dirección de un siniestro: qué dice, no dónde queda.

Parte de `src/cruce/emparejar.py:normalizar_direccion` (mismos tipos de vía y la misma
forma de quitar la placa), pero conserva el orden de las vías, la letra y el BIS, y además
reconoce el kilometraje en todos los formatos vistos en la capa y los lugares de
referencia. Nada se adivina: lo ambiguo queda marcado.

Tipos de dirección (`tipo`):
  vacia             sin texto (todo el Geoportal ANSV).
  cruce             dos vías que se cruzan («CARRERA 18 CALLE 13 B BIS»).
  cruce_inferido    la segunda vía viene sin tipo («Calle 44 con 20», «CL 13C Nº 13A-40»):
                    se le da el tipo complementario (CL ↔ CR). [Nuestra] Solo con calle y
                    carrera; con diagonal o transversal no se infiere.
  paralelas         dos vías del mismo tipo («CALLE 9 A CALLE 19 C»): no se cruzan.
  via_sola          una sola vía urbana interpretable.
  via_km            vía con kilometraje (abscisa).
  tramo_sin_km      vía o tramo rural nombrado, sin kilometraje.
  via_nombrada      una avenida o vía urbana por su nombre, sin número («AVENIDA SIERRA NEVADA»).
  referencia        solo un lugar (glorieta, barrio, establecimiento…).
  no_interpretable  hay texto pero nada de lo anterior.

`domiciliaria` es aparte: la dirección trae placa («# 8-20», «CALLE 8 20»). El punto
de una dirección domiciliaria queda sobre la vía principal, a menos de una cuadra del cruce.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

TIPOS = [(r"CALLE|CALL|CLLE|CLL|CL|CALE", "CL"),
         (r"CARRERA|CARRRERA|CARERA|CARR|KRA|CRA|CRE|KR|CR|CRR", "CR"),
         (r"DIAGONAL|DIAG|DIG|DG", "DG"),
         (r"TRANSVERSAL|TRANSV|TRASV|TRANV|TRSV|TRV|TV|TR", "TV"),
         (r"AVENIDA|AV|AVDA", "AV")]
COMPLEMENTO = {"CL": "CR", "CR": "CL"}

_TIPO = "|".join(p for p, _ in TIPOS)
# tipo + número + letra opcional + BIS opcional + letra tras el BIS opcional.
# La letra no puede ir seguida de otra letra (así «CL 35 CR» no toma la C de CR).
_VIA = re.compile(r"\b(?P<tipo>" + _TIPO + r")\.?\s*(?P<num>\d{1,3})(?!\d)"
                  r"(?:\s*(?P<letra>[A-WZ])(?![A-Z]))?"
                  r"(?:\s*(?P<bis>BIS)\b)?"
                  r"(?:\s*(?P<letra2>[A-WZ])(?![A-Z]))?")
# número suelto (sin tipo) con letra opcional: «con 20», «# 13A»
_NUM = re.compile(r"^\s*(?P<num>\d{1,3})(?!\d)(?:\s*(?P<letra>[A-WZ])(?![A-Z]))?(?:\s*(?P<bis>BIS)\b)?")
_MARCA_PLACA = re.compile(r"(?:N°|Nº|Nª|\bNO\b\.?|#|\bN\b\.?|\bNUMERO\b|\bNRO\.?)\s*(?=\d)")
_CONECTOR = re.compile(r"^\s*(?:CON|Y|X|CRUCE|ESQ|ESQUINA|#|-)?\s*")

# --- kilometraje -----------------------------------------------------------------------
_KM_MAS = re.compile(r"(?:\bKM|\bKL|\bKILOMETRO|\bK)?\s*(\d{1,3})\s*\+\s*(\d{1,3})\s*(M\b)?")
_KM_SOLO = re.compile(r"\b(?:KILOMETRO(?:\s+KM)?|KM|KL)\s*\.?\s*(\d{1,6})(?:\s+(\d{1,3}))?(?:\s+(\d{1,3}))?\b")
# abscisa al final de un tramo sin la palabra KM: «PUEBLO NUEVO - VALLEDUPAR - 43»,
# «TRAMO VALLEDUPAR SAN JUAN 24900»
_KM_COLA = re.compile(r"(?:-|\bTRAMO\b.*?)\s*(\d{1,6})\s*$")
# [Nuestra] Ninguna vía del municipio pasa del PR 150 (Pueblo Nuevo - Valledupar llega a ~115):
# un km mayor es un error de captura («KILOMETRO 637900») y no se interpreta.
KM_MAXIMO = 150.0
_RURAL = re.compile(r"\b(VIA|TRAMO|CARRETERA|RUTA|VARIANTE|TRONCAL|KM|KL|KILOMETRO)\b"
                    r"|^[A-Z ]+ - [A-Z ]+ - ")

# --- lugares de referencia -----------------------------------------------------------------
REFERENCIAS = {
    "glorieta": r"\bGLORIETA\b|\bROTONDA\b",
    "barrio": r"\bBARRIO\b|\bBRR?\b\.?|\bURB\b\.?|\bURBANIZACION\b|\bCONJUNTO\b",
    "manzana": r"\bMANZANA\b|\bMZ\b\.?|\bMZA\b",
    "establecimiento": r"\bCC\b|\bCENTRO COMERCIAL\b|\bCOLEGIO\b|\bHOSPITAL\b|\bCLINICA\b"
                       r"|\bESTACION\b|\bBOMBA\b|\bPARQUE\b|\bIGLESIA\b|\bUNIVERSIDAD\b"
                       r"|\bTERMINAL\b|\bMERCADO\b|\bPUENTE\b|\bENTRADA\b|\bFRENTE\b|\bDIAG\.",
}


@dataclass
class Via:
    tipo: str
    num: int
    letra: str = ""
    bis: bool = False
    inferida: bool = False

    @property
    def clave(self) -> tuple:
        """Llave para comparar con la nomenclatura: (tipo, número, letra, bis)."""
        return (self.tipo, self.num, self.letra, self.bis)

    @property
    def clave_numero(self) -> tuple:
        return (self.tipo, self.num)

    def __str__(self) -> str:
        return " ".join(p for p in (self.tipo, str(self.num), self.letra,
                                    "BIS" if self.bis else "") if p)


@dataclass
class Direccion:
    texto: str
    tipo: str
    vias: list = field(default_factory=list)
    domiciliaria: bool = False
    km: float | None = None
    km_nota: str = ""
    tramo: str = ""
    referencias: list = field(default_factory=list)

    @property
    def via_1(self) -> Via | None:
        return self.vias[0] if self.vias else None

    @property
    def via_2(self) -> Via | None:
        return self.vias[1] if len(self.vias) > 1 else None


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def limpiar(valor) -> str:
    """Mayúsculas, sin tildes, sin saltos de línea y con letras y dígitos separados."""
    if not isinstance(valor, str):
        return ""
    t = sin_tildes(valor).upper().replace("\n", " ")
    t = re.sub(r"(?<=[A-Z])(?=\d)", " ", t)                # «CARRERA19D» -> «CARRERA 19D»
    t = re.sub(r"(?<=[A-Z])BIS\b", " BIS", t)               # «13ABIS» -> «13A BIS»
    t = re.sub(r"\bBIS(?=\d)", "BIS ", t)                   # «6BIS1» -> «6 BIS 1»
    # «CALLE 6 NORTE» -> «CALLE 6 N»: el IGAC escribe así el sufijo cardinal («CALLE 6N»)
    t = re.sub(r"(?<=\d)(\s*[A-Z]?)\s*\bNORTE\b", r"\1 N", t)
    t = re.sub(r"(?<=\d)(\s*[A-Z]?)\s*\bSUR\b", r"\1 S", t)
    t = re.sub(r"(?<=\d)(?=[A-Z]{2,})", " ", t)            # «16CRA» -> «16 CRA»
    return " ".join(t.split())


def canon_tipo(tipo: str) -> str:
    for patron, canon in TIPOS:
        if re.fullmatch(patron, tipo):
            return canon
    return tipo


def _via(m: re.Match) -> Via:
    letra = m.group("letra") or ""
    bis = bool(m.group("bis"))
    if bis and not letra and m.group("letra2"):
        letra = m.group("letra2")
    return Via(canon_tipo(m.group("tipo")), int(m.group("num")), letra, bis)


def _km_entero(n: str) -> tuple[float, str]:
    if len(n) >= 5:
        return int(n) / 1000, "en_metros"
    if len(n) == 4:
        return int(n[:2]) + int(n[2:]) / 100, "cuatro_digitos"
    return float(n), ""


def leer_km(texto: str) -> tuple[float | None, str]:
    """-> (km, nota). Formatos [Nuestra, a partir de los vistos en la capa]:

    «KM 63+800», «4 + 900» -> 63,8 / 4,9; «53 + 85M» -> 53,085 (metros explícitos);
    «+85» sin «M» -> 53,085 con nota «metros_cortos» (podría ser 53,850);
    «KILOMETRO 85200», «KM 102600» (5–6 dígitos) -> metros: 85,2 / 102,6, nota «en_metros»;
    «KILOMETRO 1500» (4 dígitos) -> km y centenas: 15,0, nota «cuatro_digitos». Leído en
    metros (1,5) dejaba 2 de los 4 casos con vecinos a 11–13 km de su tramo; leído así, los
    4 quedan a ≤ 500 m (corte 2026-10-05, docs/diagnostico_ubicacion.md);
    «KILOMETRO 52 400 0» (plantilla km, metros, 0) -> 52,4, nota «plantilla»;
    «KM 110», «KM 2» -> kilómetros enteros;
    «PUEBLO NUEVO - VALLEDUPAR - 43» -> 43, nota «sin_prefijo»;
    otra combinación -> None, nota «ambiguo».
    """
    m = _KM_MAS.search(texto)
    if m and (m.group(0).lstrip().startswith("K") or _RURAL.search(texto)):
        a, b = int(m.group(1)), m.group(2)
        nota = ""
        if m.group(3):
            nota = "metros_explicitos"
        elif len(b) < 3:
            nota = "metros_cortos"
        return a + int(b) / 1000, nota
    m = _KM_SOLO.search(texto)
    if m:
        n, b, c = m.group(1), m.group(2), m.group(3)
        if b is not None:
            if c is not None and int(c) == 0 and len(n) <= 3:
                return int(n) + int(b) / 1000, ("plantilla" if len(b) == 3 else "metros_cortos")
            if c is None and int(b) == 0 and len(n) <= 3:
                return float(n), "plantilla"
            return None, "ambiguo"
        return _km_entero(n)
    if _RURAL.search(texto):
        m = _KM_COLA.search(texto)
        if m:
            n = m.group(1)
            km, nota = _km_entero(n)
            return km, nota or "sin_prefijo"
    return None, ""


def _tramo(texto: str) -> str:
    """Nombre del tramo rural: el texto sin kilometraje, ruta, prefijos ni signos."""
    t = re.sub(r"\b(KILOMETRO|KM|KL)\b\s*\.?[\d\s+M]*", " ", texto)
    t = re.sub(r"\d+\s*\+\s*\d+", " ", t)
    t = re.sub(r"\bRUTA\s*\w+", " ", t)
    t = re.sub(r"\b(VIA|TRAMO|CARRETERA|TRONCAL|SECTOR|PRINCIPAL)\b", " ", t)
    t = re.sub(r"[^A-Z ]", " ", t)
    return " ".join(t.split())


def leer(valor) -> Direccion:
    texto = limpiar(valor)
    if not texto:
        return Direccion(texto="", tipo="vacia")
    referencias = [r for r, p in REFERENCIAS.items() if re.search(p, texto)]
    km, km_nota = leer_km(texto)
    if km is not None and km > KM_MAXIMO:
        km, km_nota = None, "fuera_de_rango"
    es_rural = bool(_RURAL.search(texto)) and not re.search(r"\bVIA\s+(CALLE|CARRERA)\b", texto)

    marcado = _MARCA_PLACA.sub(" # ", texto)
    vias, fin = [], 0
    for m in _VIA.finditer(marcado):
        vias.append(_via(m))
        fin = m.end()
        if len(vias) == 2:
            break
    domiciliaria = "#" in marcado
    if len(vias) == 1 and vias[0].tipo in COMPLEMENTO:
        # segunda vía sin tipo: «CL 13C # 13A - 40», «Calle 44 con 20»
        resto = marcado[fin:]
        con = _CONECTOR.match(resto)
        if con and con.group(0).strip():
            n = _NUM.match(resto[con.end():])
            if n:
                vias.append(Via(COMPLEMENTO[vias[0].tipo], int(n.group("num")),
                                n.group("letra") or "", bool(n.group("bis")), inferida=True))
    if len(vias) == 2:
        # placa tras la segunda vía: «CALLE 16 CARRERA 17A 45», «CR 9 CL 8-20»
        m2 = list(_VIA.finditer(marcado))
        tras = marcado[m2[1].end():] if len(m2) > 1 and not vias[1].inferida else ""
        if re.match(r"^\s*-?\s*\d{1,3}\b", tras):
            domiciliaria = True

    if km is not None or km_nota in ("ambiguo", "fuera_de_rango"):
        tipo = "via_km"
    elif len(vias) == 2:
        if vias[0].tipo == vias[1].tipo and not vias[1].inferida:
            tipo = "paralelas"
        else:
            tipo = "cruce_inferido" if vias[1].inferida else "cruce"
    elif len(vias) == 1:
        tipo = "via_sola"
    elif es_rural:
        tipo = "tramo_sin_km"
    elif re.search(r"\b(AVENIDA|AV|AVDA|DOBLE CALZADA|CIRCUNVALAR|MARGINAL)\b\.?\s+[A-Z]{3,}", texto):
        tipo = "via_nombrada"
    elif referencias:
        tipo = "referencia"
    else:
        tipo = "no_interpretable"
    tramo = _tramo(texto) if tipo in ("via_km", "tramo_sin_km") else ""
    return Direccion(texto=texto, tipo=tipo, vias=vias, domiciliaria=domiciliaria, km=km,
                     km_nota=km_nota, tramo=tramo, referencias=referencias)


def leer_nombre_via(nombre) -> Via | None:
    """Nombre de un eje de la nomenclatura IGAC u OSM («CARRERA 19 C», «Carrera 40b») -> Via.
    Solo si el nombre es exactamente una vía numerada; «AVENIDA SIMON BOLIVAR» -> None."""
    t = limpiar(nombre)
    m = _VIA.fullmatch(t.strip()) or _VIA.match(t)
    if not m or t[m.end():].strip():
        return None
    return _via(m)


# --- tramos rurales ------------------------------------------------------------------------
# [Nuestra] El mismo tramo aparece escrito de decenas de formas («PUEBLO NUEVO V»,
# «PEBLO NUEVO VALLEDUPAR», «P NUEVO VPAR»). Se agrupa por palabras clave, en este orden; lo
# que no encaja queda como «otro» y no entra al control de abscisa. «PUEBLO BELLO -
# VALLEDUPAR» es la errata conocida del tramo Pueblo Nuevo (docs/plan_carga_portal_policia.md).
TRAMOS = [
    ("Pueblo Nuevo - Bosconia", r"BOSCONIA"),
    ("San Roque - La Paz", r"SAN\s*R"),
    ("Valledupar - La Paz", r"LA\s*PAZ|LAPAZ"),
    # «KILOMETRO 13 900 0 VIA VALLEDUPAR SAN»: el campo llega cortado; el control de abscisa
    # dice si esos puntos caen donde los de San Juan (docs/diagnostico_ubicacion.md).
    ("Valledupar - San Juan", r"SAN\s*J|SANJUAN|VALLEDUPAR\s+SAN$"),
    ("Valledupar - Río Seco", r"RIO\s*SECO"),
    ("Pueblo Nuevo - Valledupar", r"PUEB|PEBL|PUBL|P\s*NUEV|NUEVO|PINUEDO|PUEBLO\s*BELLO"),
]


def tramo_canonico(tramo: str) -> str:
    if not tramo:
        return ""
    for nombre, patron in TRAMOS:
        if re.search(patron, tramo):
            return nombre
    return "otro"
