---
name: Sala de control · Semáforos SAST
description: Muro de video de sala de control para los cinco cruces semaforizados con cámaras SAST de Valledupar.
colors:
  sala: "#05070a"
  sala-2: "#0a0d11"
  bisel: "#15191d"
  bisel-2: "#1d2328"
  bisel-luz: "#2c343b"
  pantalla: "#0a0f13"
  pantalla-2: "#0f151a"
  filete: "#1f2a32"
  filete-2: "#2b3843"
  tinta: "#e8eef2"
  tinta-2: "#a9b6bf"
  tinta-3: "#7d8b95"
  rojo: "#ff3b30"
  rojo-off: "#2a0f0e"
  ambar: "#ffb000"
  ambar-off: "#2b210a"
  verde: "#1fe08a"
  verde-off: "#0b2619"
  sast: "#ff7a1a"
  sast-off: "#3a1f0c"
  cajon: "#ffd400"
  tally: "#ff2d2d"
  ciclo-1: "#4b565e"
  ciclo-2: "#76828b"
  ciclo-3: "#aab4bb"
  ciclo-4: "#e3e8eb"
typography:
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "1.9rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.005em"
  headline:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.01em"
  title:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.01em"
  numeral:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "1.45rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tnum"
  body:
    fontFamily: "Public Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.45
  caption:
    fontFamily: "Public Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 400
    lineHeight: 1.4
  subtitle:
    fontFamily: "Public Sans, Segoe UI, system-ui, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 500
    lineHeight: 1.35
  label:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.06em"
rounded:
  hairline: "3px"
  chip: "4px"
  control: "5px"
  monitor: "6px"
  dialog: "8px"
spacing:
  gap: "10px"
  gap-movil: "8px"
  barra: "58px"
  barra-movil: "52px"
  bisel: "6px"
components:
  monitor:
    backgroundColor: "{colors.bisel}"
    rounded: "{rounded.monitor}"
    padding: "6px 6px 0"
  pantalla:
    backgroundColor: "{colors.pantalla}"
    rounded: "{rounded.hairline}"
  rotulo:
    textColor: "{colors.tinta-3}"
    typography: "{typography.label}"
    height: "24px"
    padding: "0 4px 0 6px"
  button:
    backgroundColor: "{colors.bisel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.control}"
    height: "34px"
    padding: "0 14px"
  chip:
    backgroundColor: "{colors.pantalla}"
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.chip}"
    height: "32px"
    padding: "0 10px"
  chip-pressed:
    backgroundColor: "{colors.pantalla-2}"
    textColor: "{colors.tinta}"
  sello:
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.chip}"
    padding: "5px 9px"
  sello-borrador:
    textColor: "{colors.ambar}"
  lente:
    size: "13px"
    rounded: "50%"
  dialog:
    backgroundColor: "{colors.bisel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.dialog}"
    padding: "22px 24px"
---

# Design System: Sala de control · Semáforos SAST

## Overview

**Creative North Star: "La sala de control de la STTV"**

El sistema es un muro de video en una sala a oscuras. Todo lo que se ve es hardware de sala: monitores con bisel grafito, pantallas negras con un leve reflejo de vidrio, un rótulo de operador bajo cada pantalla y una luz tally que dice cuál está al aire. La información vive dentro de las pantallas; nada flota sobre el muro salvo el subtítulo de la presentación, la ventana de fuentes y el tooltip.

La luz es el contenido. Los únicos colores saturados son los que emite un semáforo de campo (rojo, ámbar y verde con brillo LED real), el naranja de las cámaras SAST y el amarillo de la demarcación del cajón. El resto es negro, grafito y tinta fría. Los números se leen como se leen en la calle: en displays de 7 segmentos, del color de la luz que cuentan.

La densidad es de sala de control, no de página: muchos monitores pequeños y uno grande, rótulos condensados, cifras tabulares. El movimiento sirve para explicar el ciclo (la aguja barre, el cruce se dibuja, el monitor vuela a la pantalla principal) y desaparece con movimiento reducido. Las indicaciones semafóricas nunca dependen solo del color: forma, palabra y posición las acompañan (rayado para el amarillo, punteado e intermitencia para el despeje, SIGA / PREVENCIÓN / PARE / NO INICIE bajo cada cabeza).

**Key Characteristics:**
- Negro de sala con biseles grafito; el color saturado se reserva a luces emitidas.
- Monitor = bisel + pantalla + rótulo de operador + tally.
- Displays de 7 segmentos para todo contador; Barlow Condensed para rótulos y cifras, Public Sans para texto.
- Lentes LED con gradiente radial y halo; apagados con su tono "off" propio, nunca grises.
- Un solo bucle de animación (ticker de GSAP) y movimiento que se apaga con `prefers-reduced-motion`.

## Colors

Paleta de sala a oscuras: neutros fríos casi negros y tres luces de semáforo que son, literalmente, luz.

### Primary
- **Rojo de lente** (rojo): la luz roja de las cabezas, los arcos rojos del reloj (atenuados al 26–32 % de opacidad para que el verde domine la lectura), la preparación TIRA–TIV y el despeje peatonal intermitente. Es el color por defecto de los displays de 7 segmentos.
- **Ámbar de lente** (ambar): amarillo vehicular, siempre rayado en los arcos; también la hora de Bogotá en el display de la barra y el sello «Accesos por validar».
- **Verde de lente** (verde): verde vehicular y peatonal, plan vigente (punto en el chip), sello «En vivo» y tally de vista previa.

### Secondary
- **Naranja SAST** (sast): exclusivo de las cámaras SAST (cuerpo y cono de barrido del marcador), estado «Operativo» de la ficha, enlaces de texto, anillo de foco y selección.
- **Rojo tally** (tally): la luz «al aire» del rótulo del monitor que está en la pantalla principal, el punto del botón «Presentar» y el contorno del monitor en vuelo.

### Tertiary
- **Amarillo de cajón** (cajon): solo la demarcación del cajón amarillo (bloqueo de intersección) en el diagrama del cruce, como en el inventario de señalización.
- **Escala de ciclo, grafito a blanco** (ciclo-1 a ciclo-4): duración del ciclo en la programación semanal (≤55 s, ≤80 s, ≤95 s, ≥100 s). La luminancia sube con la duración y está validada para leerse sin tono.

### Neutral
- **Negro de sala** (sala, sala-2): fondo del cuerpo, con un radial que aclara apenas la parte alta.
- **Bisel grafito** (bisel, bisel-2, bisel-luz): marcos de monitor en gradiente a 160°, fondo de botones y ventana de diálogo; bisel-luz es el borde de botones.
- **Pantalla apagada** (pantalla, pantalla-2): interior de cada pantalla, en radial.
- **Filete** (filete, filete-2): divisores, bordes de chips, sellos y celdas de tabla.
- **Tinta** (tinta, tinta-2, tinta-3): texto principal, secundario y de rótulo o nota.
- **Tonos apagados** (rojo-off, ambar-off, verde-off, sast-off): lente o segmento apagado. Cada luz tiene su apagado teñido; un lente apagado no es gris.

### Named Rules
**The Luz Emitida Rule.** El color saturado se reserva a lo que en la sala o en la calle emite luz: lentes, contadores, tallies, cámaras SAST y la demarcación del cajón. La interfaz (botones, chips, paneles) es grafito y tinta. Los vehículos y peatones simulados son objetos del mundo y llevan colores de calle; no son interfaz.

**The Apagado Teñido Rule.** Todo lente y todo segmento apagado conserva un rastro de su color (tokens `-off`, o `color-mix` al 9 % sobre negro en los displays). Un semáforo apagado sigue mostrando qué luz tiene.

## Typography

**Display Font:** Barlow Condensed (con Arial Narrow, Roboto Condensed)
**Body Font:** Public Sans (con Segoe UI, system-ui)
**Label/Mono Font:** Barlow Condensed para rótulos; los contadores no usan fuente, son displays SVG de 7 segmentos.

**Character:** Barlow Condensed es la rotulación de consola: estrecha, firme, en mayúsculas espaciadas para los rótulos del operador y en caja normal para nombres de cruce y cifras. Public Sans lleva las frases de explicación, con voz institucional y legible en proyector.

### Hierarchy
- **Display** (700, 1.9rem, 1): nombre del cruce en la pantalla principal (1.45rem en celular).
- **Headline** (600, 1.375rem, 1): título de la barra del operador.
- **Title** (700, 1.15rem, 1.1): título de cada monitor de análisis; nombres de fuente a 1.06rem/600.
- **Numeral** (700, 1.45rem, 1, cifras tabulares): cifras de la ficha SAST; los KPI del plan bajan a 1.15rem.
- **Body** (400, 0.9375rem, 1.45): texto corrido; explicaciones a 0.82–0.88rem; frase de fase a 1.05rem con 34ch de medida.
- **Caption** (400, 0.7–0.82rem): notas y etiquetas de cifras en tinta-3.
- **Subtitle** (500, 1.35rem, 1.35): subtítulos del modo presentación, centrados, con la palabra clave en Barlow Condensed 700.
- **Label** (600, 0.78rem, 0.06em, MAYÚSCULAS): rótulo de operador; botones a 0.95rem/0.04em, sellos a 0.82rem/0.05em y pestañas a 0.86rem/0.05em, todos en mayúsculas.

La raíz escala con la pantalla: 16px, 17.5px desde 1700px y 20px desde 2200px, para que el muro se lea proyectado.

### Named Rules
**The Contador de Campo Rule.** Todo contador que el semáforo real muestra (regresiva de cada cabeza, segundos del ciclo, hora de Bogotá) se dibuja con el display de 7 segmentos en el color de la luz que cuenta, nunca con texto tipográfico.

**The Cifra Tabular Rule.** Cifras de tablas, barras y KPI van con `tabular-nums` para que no bailen mientras corre el ciclo.

## Layout

Un muro en rejilla de tres columnas y dos filas, alto de ventana menos la barra del operador (58px): columna de fuentes (`minmax(190px, 15vw)`) con el monitor del mapa y los cinco cruces apilados; pantalla principal flexible que ocupa la fila superior central; columna de análisis (`minmax(320px, 24vw)`) con tres monitores apilados; y una franja inferior (`clamp(150px, 20vh, 210px)`) con la línea de tiempo del ciclo bajo la principal y el análisis. Separación uniforme de 10px entre monitores y en el borde del muro.

La barra del operador es una rejilla de tres columnas: marca a la izquierda, hora en 7 segmentos y tipo de día al centro, acciones a la derecha.

**Pantallas bajas de escritorio** (1366×768, 1280×720; consultas de contenedor sobre el alto de cada monitor): primero se ocultan las ayudas que repiten algo visible. Con el reloj del ciclo de 120px de alto o menos, la leyenda deja solo «despeje peatonal» y «aguja = ahora». Con la explicación de 200px o menos, desaparece la frase «Ahora rige…», los cuatro indicadores pasan a una línea y cada fase usa su texto corto. Con 160px o menos (1280×720), la línea de indicadores también se oculta. La regla: la fase en curso se ve siempre entera y ningún texto queda cortado a la mitad.

**Por debajo de 1180px** el muro se vuelve columna de dos: las fuentes pasan a una tira horizontal desplazable (monitores de 200px × 104px), la principal ocupa `minmax(460px, 68vh)`, el análisis se reparte en monitores de mínimo 300px y la franja queda al final.

**Por debajo de 760px** todo va en una columna, la barra baja a 52px y el gap a 8px; los textos de los botones desaparecen y quedan sus iconos; la principal mide `minmax(440px, 78vh)`; marcadores, sellos y leyenda se compactan.

## Elevation & Depth

La profundidad es física, de sala: los monitores son objetos con sombra ambiental debajo y un brillo de arista arriba; las pantallas se hunden con sombra interior; la luz se mide en halos (`box-shadow` y `drop-shadow` del color de la propia luz). Los paneles internos son planos y se separan por filetes.

### Shadow Vocabulary
- **Monitor** (`box-shadow: 0 14px 30px -12px rgba(0,0,0,.85), 0 2px 0 rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.07), inset 0 0 0 1px rgba(255,255,255,.025)`): todo bisel del muro.
- **Pantalla hundida** (`box-shadow: inset 0 0 0 1px #000, inset 0 0 28px rgba(0,0,0,.55)`): interior de cada pantalla.
- **Lente encendido** (`box-shadow: 0 0 10px 2px color-mix(in srgb, <luz> 70%, transparent), 0 0 24px color-mix(in srgb, <luz> 35%, transparent)`): halo doble de cada luz de cabeza.
- **LED pequeño** (`box-shadow: 0 0 6px <luz>`): tallies, puntos de estado y LEDs de fuente.
- **Display** (`filter: drop-shadow(0 0 3px color-mix(in srgb, <luz> 55%, transparent))`): resplandor de los 7 segmentos.
- **Ventana** (`box-shadow: 0 30px 80px rgba(0,0,0,.8)`): diálogo de fuentes, con fondo velado y desenfoque de 3px.

### Named Rules
**The Brillo Es Del Color Rule.** Un halo siempre es del color de la luz que lo emite. No hay sombras de color ajenas ni sombras duras desplazadas.

## Shapes

Esquinas apenas suavizadas, como hardware: 6px en el bisel del monitor, 3px en la pantalla, 5px en botones, 4px en chips y sellos, 3px en códigos, etiquetas y burbujas, 8px en la ventana de diálogo. Los lentes vehiculares y los LEDs son círculos; los lentes peatonales y de flecha son cuadrados de 3px con pictograma SVG. El reloj del ciclo es un conjunto de anillos concéntricos, uno por grupo con el G1 por fuera, que empiezan a las 12 y avanzan en sentido horario. La línea de tiempo se dibuja con barras rectas. Las líneas punteadas se reservan a dos significados: despeje peatonal y equipo SAST no operativo.

## Components

### Monitor (firma)
Bisel grafito en gradiente (160°, bisel-2 → bisel), 6px de padding sin padding inferior, pantalla negra radial con reflejo de vidrio diagonal (`linear-gradient(115deg, rgba(255,255,255,.035), transparent 32%)`) y rótulo de operador de 24px abajo: texto condensado en mayúsculas a la izquierda («CRUCE · CONTROLADOR/CRUCE») y tally a la derecha. Los monitores fuente son botones: al pasar el cursor suben 1px y su pantalla gana un filete; el seleccionado tiene filete tally y rótulo en tinta.

### Tally
Punto de 7px. Apagado `#2a1414`; **al aire** (on) rojo tally con halo; **vista previa** (pvw) verde durante 320ms antes de pasar a al aire, como en un switcher de video.

### Display de 7 segmentos
SVG de dígitos de 10×18 con 7 polígonos inclinados −6°, dos puntos fijos opcionales y segmentos apagados con su color al 9 % sobre negro. Lo usan la hora de Bogotá (ámbar), la regresiva de cada cabeza (color de su luz), la cuenta de cada monitor fuente y el centro del reloj grande (segundos del ciclo en tinta, o restante del grupo en foco en su color).

### Reloj del ciclo (anillo)
Tres capas SVG superpuestas: arcos quietos (se repintan solo al cambiar de plan), capa móvil que gira por `transform` en el compositor (aguja blanca; en los mini, cuentas LED con halo por grupo) y centro (display, cambia una vez por segundo). Verde sólido, amarillo rayado a 45°, rojo atenuado, despeje punteado. El reloj grande lleva marcas cada 10 s y números cada 20 s; su entrada es un fundido con escala desde 0.94. El monitor del reloj muestra siempre, junto al plan y su ciclo, las dos cifras clave del plan: el rojo más largo y el verde promedio de los flujos vehiculares (sin flechas ni peatonales).

### Diagrama del cruce
Norte del mapa arriba, sin rotar (fiel al mapa y a la imagen satelital). Cada vía lleva su nombre completo en versalitas condensadas sobre su eje, derecho y lejos del cruce (una vez por nombre). Un cruce largo, con pares lejos del centro, trae su propio encuadre (`vista`).

### Cabeza semafórica
Caja negra (`#0d1114`) de esquinas de 6px con lentes apilados (rojo, ámbar, verde; peatonal con figura quieta o caminando; flecha), la regresiva de 7 segmentos debajo y la palabra de estado (SIGA, PREVENCIÓN, PARE, NO INICIE) en Barlow Condensed 700 del color de la luz. El despeje es el lente rojo intermitente a 0.5 s. En el diagrama, la cabeza va paralela a la vía que controla (en columna si la vía es más vertical, en fila si es más horizontal, y girada lo que falte, a lo sumo 45°, para que el contador se lea) y sobre el andén derecho, al lado de la cola y antes de la línea de pare: nunca tapa la calzada. La peatonal va a lo largo del andén exterior, junto a su cebra.

### Buttons
- **Shape:** esquinas de control (5px), 34px de alto.
- **Primary:** gradiente grafito (`#1a2026` → `#12171b`), borde bisel-luz, rótulo en mayúsculas condensado. «Presentar» lleva el punto tally y borde teñido de tally.
- **Hover / Focus:** borde más claro y gradiente un tono arriba; al presionar baja 1px; pulsado (`aria-pressed`) con borde naranja SAST. Foco global: contorno naranja SAST de 2px separado 2px.

### Chips
- **Style:** fondo de pantalla, filete-2, Barlow Condensed 0.9rem/600, muestra de color de ciclo de 10px.
- **State:** pulsado con borde tinta-2 y texto blanco; plan vigente con punto LED verde; plan sin horario en el controlador con borde discontinuo y 62 % de opacidad; deshabilitado al 45 %.

### Sellos
Etiquetas de estado sobre la pantalla principal («En vivo», «Fase ilustrativa», «Accesos por validar»): mayúsculas condensadas, filete-2, fondo negro al 75 %. «Borrador» en ámbar; «En vivo» con punto LED verde.

### Navigation
Pestañas dentro de un monitor: mayúsculas condensadas en tinta-3, la activa en tinta con subrayado tinta-2 de 2px. La navegación principal es el propio muro: elegir un monitor fuente o un semáforo del mapa lo manda a la pantalla principal.

### Movimiento
Un solo ticker de GSAP mueve todo lo que corre por cuadro (`lagSmoothing(0)`, se pausa con la pestaña oculta; sin GSAP cae a `requestAnimationFrame`). El monitor elegido **vuela** a la pantalla principal: un clon con contorno tally viaja 0.55 s en `expo.inOut`, lo cruza un barrido de luz y se desvanece en 0.3 s; el contenido nuevo se monta a los 380 ms sin esperar la animación. El cruce **se dibuja**: trazos de vía con `stroke-dashoffset` 0.9 s escalonados, luego demarcación, cebras, cabezas y el lienzo. Los subtítulos entran por CSS (0.4 s, sube 8px). La curva propia es `cubic-bezier(.16, 1, .3, 1)` (y `expo.out` en GSAP). Con `prefers-reduced-motion` no hay vuelo, ni dibujo, ni barrido de cámaras, ni parpadeo, ni transiciones de botones y fuentes; la aguja y los contadores siguen marcando el tiempo.

## Do's and Don'ts

### Do:
- **Do** meter toda vista nueva en un monitor: bisel, pantalla, rótulo de operador en mayúsculas condensadas y tally.
- **Do** usar el display de 7 segmentos para cualquier contador en tiempo real, en el color de la luz que cuenta.
- **Do** acompañar cada estado semafórico con forma o palabra: amarillo rayado, despeje punteado o intermitente, palabra SIGA / PREVENCIÓN / PARE / NO INICIE.
- **Do** dar a cada luz su tono apagado (`-off`) y su halo del mismo color.
- **Do** colgar cualquier animación por cuadro del ticker único y darle una salida con `prefers-reduced-motion`.
- **Do** marcar con un sello visible todo lo ilustrativo o pendiente de validar.

### Don't:
- **Don't** rellenar botones, chips o paneles con rojo, ámbar o verde: esos colores significan una indicación semafórica (un punto LED o un borde de estado sí los usan).
- **Don't** usar el naranja SAST para nada que no sea cámara SAST, foco, selección o enlace.
- **Don't** apagar un lente en gris neutro; el apagado lleva su tono.
- **Don't** escribir un contador en tipografía cuando el semáforo real lo muestra en segmentos.
- **Don't** abrir un segundo bucle de `requestAnimationFrame` junto al ticker.
- **Don't** usar sombras duras desplazadas ni halos de un color distinto al de su luz.
