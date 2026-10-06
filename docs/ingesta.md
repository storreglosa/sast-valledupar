# Ingesta de insumos a `data/raw/`

`data/raw/` es de solo lectura y no se versiona: los comparendos traen cédula, nombre y placa.
Los insumos los copia Santiago desde la raíz del repo. `scripts/00_manifiesto.py` congela el
SHA-256 de cada archivo en `docs/manifiesto_raw.csv` y avisa si alguno cambia después.

```bash
mkdir -p data/raw/comparendos data/raw/equipos data/raw/pot data/raw/red_vial data/raw/portal
cp "/mnt/d/Users/Storreglosa/OneDrive/Escritorio/LINEA BASE SAST/registrosComparendoTotalesExcel 2023 - 2026 1.zip" data/raw/comparendos/2026-10-04_sttv_comparendos-2023-2026.zip
cp "/mnt/d/Users/Storreglosa/OneDrive/Trabajo/04. Secretaría de tránsito Valledupar/06. Equipos SATS/Equipos SAST Actualizado.xlsx" data/raw/equipos/2026-10-06_sttv_equipos-sast.xlsx
cp "/mnt/d/Users/Storreglosa/OneDrive/Trabajo/04. Secretaría de tránsito Valledupar/06. Equipos SATS/01. SIG/01. Capas generadas/Zona de influencia/Zona de influencia."{shp,shx,dbf,prj,cpg} data/raw/equipos/
cp ~/Claude_code/POT_Valledupar/data/processed/publicacion/POT_Valledupar_{Limites_Administrativos,Clasificacion_Suelo,Movilidad_Vial}.gdb.zip data/raw/pot/
cp ~/Claude_code/red-vial-valledupar/data/processed/2026-08-05_osm_red-vial-valledupar.gpkg data/raw/red_vial/
```

Siniestros: `scripts/00_snapshot_portal.py` los descarga del portal ANSV (solo lectura) a
`data/raw/portal/AAAA-MM-DD_portal_siniestros.parquet`. Necesita el `.env` con
`PORTAL_URL`, `PORTAL_USERNAME` y `PORTAL_PASSWORD` (copiarlo de ArcgisManage: `cp ../ArcgisManage/.env .env`).
