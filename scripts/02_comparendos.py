"""Etapa 2 — Comparendos: lectura sin datos personales, depuración y clasificación del medio.

Salida: data/processed/comparendos.parquet (sin cédula, nombre ni placa),
outputs/tables/comparendos_{apartados,malformadas,diagnostico}.csv.
"""

import pandas as pd

import _entorno  # noqa: F401
from sast.comparendos import PERSONALES, depurar_duplicados, leer_zip, tipificar
from sast.equipos import equipos_operativos
from sast.rutas import OUTPUTS, PROCESSED

TABLAS = OUTPUTS / "tables"


def main() -> None:
    crudo, malas, fuente = leer_zip()
    assert not (set(crudo.columns) & PERSONALES), "se coló un campo personal"
    d = tipificar(crudo)
    decl = crudo.attrs["totales_declarados"]
    print(f"{fuente}: {len(crudo):,} filas leídas = suma de los pies «Total:» ({sum(decl.values()):,}); "
          f"{len(malas)} filas malformadas apartadas")
    if d["fecha"].isna().any():
        raise SystemExit(f"{d['fecha'].isna().sum()} fechas no interpretables")
    print(f"  fechas {d['fecha'].min().date()} a {d['fecha'].max().date()}")
    print(f"  direcciones con <PLACA> enmascarada: {d['direccion'].str.contains('<PLACA>', regex=False).sum()}")
    futuras = d["fecha"].gt(pd.Timestamp.today().normalize())
    if futuras.any():
        raise SystemExit(f"{futuras.sum()} comparendos con fecha futura")

    dep, apartados = depurar_duplicados(d)
    print(f"  duplicados (nro, código): {len(apartados)} filas apartadas; "
          f"{int(dep['dup_conflicto'].sum())} conservadas con conflicto de fecha/dirección/medio")
    multi = dep.groupby("nro")["codigo"].nunique().gt(1).sum()
    print(f"  comparendos con más de un código: {multi}")
    assert len(dep) + len(apartados) == len(crudo), "no cuadra el conteo de depuración"

    raros = dep[~dep["codigo"].str.match(r"^[A-Z]\d{2}$")]["codigo"].value_counts()
    if len(raros):
        print(f"  AVISO: códigos con formato inesperado: {raros.to_dict()}")

    # medio SAST: además del patrón, la fecha debe ser posterior al inicio de su equipo
    eq = equipos_operativos()
    inicio_min = eq["fecha_inicio"].min()
    sast_antes = dep["medio"].eq("sast") & dep["fecha"].lt(inicio_min)
    print(f"  SAST: {dep['medio'].eq('sast').sum():,} registros, primero {dep.loc[dep['medio'].eq('sast'), 'fecha'].min().date()}; "
          f"{sast_antes.sum():,} antes del inicio de operación ({inicio_min.date()}) — "
          "se mantienen fuera de la línea base (pruebas o arranque anticipado, por confirmar)")
    dep["sast_antes_inicio"] = sast_antes

    print("\nMedio × estado de la coordenada:")
    print(pd.crosstab(dep["medio"], dep["coord_estado"], margins=True).to_string())
    print("\nMedio × año:")
    print(pd.crosstab(dep["medio"], dep["fecha"].dt.year, margins=True).to_string())

    dep.to_parquet(PROCESSED / "comparendos.parquet", index=False)
    apartados[["archivo", "nro", "fecha", "codigo", "medio", "fuente", "coord_estado",
               "estado_resolucion"]].to_csv(TABLAS / "comparendos_apartados.csv", index=False,
                                            encoding="utf-8-sig")
    malas.to_csv(TABLAS / "comparendos_malformadas.csv", index=False, encoding="utf-8-sig")
    diag = pd.DataFrame([
        ("filas_leidas", len(crudo)), ("total_declarado_pies", sum(decl.values())),
        ("filas_malformadas", len(malas)),
        ("direcciones_placa_enmascarada", int(d["direccion"].str.contains("<PLACA>", regex=False).sum())),
        *[(f"codigo_formato_inesperado_{k}", v) for k, v in raros.items()],
        ("duplicados_apartados", len(apartados)), ("depurados", len(dep)),
        ("dup_conflicto", int(dep["dup_conflicto"].sum())),
        ("notificacion_1900", int(dep["bandera_notificacion_1900"].sum())),
        *[(f"medio_{k}", v) for k, v in dep["medio"].value_counts().items()],
        *[(f"coord_{k}", v) for k, v in dep["coord_estado"].value_counts().items()],
        ("sast_antes_inicio", int(sast_antes.sum())),
    ], columns=["indicador", "valor"])
    diag.to_csv(TABLAS / "comparendos_diagnostico.csv", index=False, encoding="utf-8-sig")
    print(f"\n-> data/processed/comparendos.parquet ({len(dep):,} filas)")


if __name__ == "__main__":
    main()
