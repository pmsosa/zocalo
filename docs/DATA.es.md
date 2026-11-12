# Guía de datos

Zócalo nunca incluye datos de encuestas ni de censos. Cada archivo viene de quien lo publica, bajo su propia licencia. Hay
dos tipos:

- **Automáticos.** Presiona *descargar* en la página Datos. Zócalo trae el archivo de quien lo publica.
- **A mano.** Quien lo publica te pide primero iniciar sesión o llenar un formulario corto. Descarga el archivo tú mismo
  y ponlo en la carpeta que se indica abajo; la página Datos muestra *listo* cuando lo encuentra.

Todos los archivos van en la **carpeta de datos**, que se define al instalar Zócalo (`./deploy.sh --datasets-dir PATH`;
de forma predeterminada `./datasets`, junto a la app). Puede estar en un disco externo. Si el disco está desconectado,
Zócalo lo dice y espera: nunca vuelve a descargar todo en otro lugar. Todo lo que hay en la carpeta se puede volver a
descargar, así que no necesita respaldo. Respalda en cambio la **carpeta de datos de la app** (la base de datos y las claves
cifradas).

## Para qué sirve cada fuente

| Fuente | Te da | Cómo | Licencia |
|---|---|---|---|
| US Census ACS PUMS 2024 | Personas de EE. UU. a partir de registros reales del censo | automática, 575 MB | dominio público |
| UK Census 2021 teaching sample | Personas de Inglaterra y Gales | automática, 37 MB | Open Government Licence |
| Canada 2021 Census PUMF | Personas de Canadá | automática, 182 MB | Statistics Canada Open Licence |
| Cooperative Election Study | Personas de EE. UU., y actitudes para las personas del censo de EE. UU. | automática, 144 MB | CC0 |
| General Social Survey | Personas de EE. UU., actitudes, preguntas reales para el índice y las pruebas | automática, 48 MB | términos de NORC |
| Afrobarometer Round 10 | Personas de 38 países africanos, preguntas, pruebas | automática, 13 MB | gratuita, con atribución |
| Latinobarómetro 2024 | Personas de 17 países latinoamericanos, preguntas, pruebas | automática, 6 MB | **no comercial** |
| World Values Survey Wave 7 | Personas de 66 países, preguntas, pruebas | **a mano** | **sin fines de lucro** |
| European Social Survey Round 11 | Personas de 31 países europeos | **a mano** | **CC BY-NC-SA** |
| Arab Barometer Wave IX | Personas de 9 países árabes | **a mano** | no comercial |
| Pew American Trends Panel | Personas de EE. UU., y el mejor material de prueba | **a mano**, ola por ola | términos de Pew |
| Twin-2K-500 | Prueba: gemelos de 2,058 personas reales | automática, 27 MB | CC BY 4.0 |
| GlobalOpinionQA | Prueba: proporciones de respuesta por país | automática, 5 MB | **CC BY-NC-SA** |
| SimBench | Prueba: proporciones de respuesta de 20 encuestas | automática, 4 MB | **CC BY-NC-SA** |

Las fuentes marcadas como no comerciales se pueden desactivar en Ajustes → Datos, para quien use Zócalo con fines
comerciales.

Después de descargar una encuesta de opinión, presiona **indexar preguntas** en la página Datos. Sus preguntas y sus
proporciones de respuesta reales aparecen entonces como "encuestas reales más parecidas" junto a tus resultados, y
quedan disponibles para la referencia de prueba *la otra encuesta más parecida*.

## Cómo conseguir las fuentes a mano

En cada ruta de abajo, `DATASETS` es tu carpeta de datos.

### World Values Survey Wave 7 → `DATASETS/wvs/`

1. Abre <https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp>.
2. Haz clic en **WVS Cross-National Wave 7 spss v6 0.zip** (o la versión más reciente).
3. Llena el formulario corto (nombre, institución, uso previsto) y acepta las condiciones de uso.
4. Descomprímelo y pon el archivo `.sav` en `DATASETS/wvs/`.

Gratis para uso sin fines de lucro. No compartas el archivo en sí.

### European Social Survey Round 11 → `DATASETS/ess/`

1. Inicia sesión, con una cuenta gratuita, en el ESS Data Portal: <https://ess.sikt.no/en/datafile/242aaa39-3bbb-40f5-98bf-bfb1ce53d8ef>
2. Descarga el **ESS11 integrated file** en formato **SPSS**.
3. Descomprímelo y pon el archivo `.sav` (con un nombre como `ESS11e04_2.sav`) en `DATASETS/ess/`.

### Arab Barometer Wave IX → `DATASETS/arab_barometer/`

1. Abre <https://www.arabbarometer.org/survey-data/data-downloads/>.
2. Haz clic en **Arab Barometer Wave IX: Data Sets** y llena el formulario corto.
3. Descomprímelo y pon el archivo `.sav` en inglés en `DATASETS/arab_barometer/`.

### Pew Research Center American Trends Panel → `DATASETS/pew/`

Las olas del panel de Pew son el mejor material para pruebas honestas, porque cada ola es una muestra grande y
cuidadosamente ponderada de adultos de EE. UU., con la redacción completa de las preguntas.

1. Crea una cuenta gratuita en <https://www.pewresearch.org/datasets/> ("My Account").
2. Abre la página de una ola, por ejemplo <https://www.pewresearch.org/dataset/american-trends-panel-wave-169/>, acepta
   los términos y descárgala.
3. Descomprímela y pon `ATP W169.sav` (o la ola que sea) en `DATASETS/pew/`. Agrega todas las olas que quieras. La ola
   más reciente se usa para construir poblaciones de Pew.

**Qué olas.** Para las pruebas, las olas más útiles se levantaron **después de la fecha de corte de entrenamiento de tu
modelo**, así que el modelo no pudo haber visto los resultados. A noviembre de 2026, las olas públicas más recientes son:

| Ola | Levantada | Tema |
|---|---|---|
| W169 | 28 abr – 4 may 2025 | clima y energía |
| W168 | 14–20 abr 2025 | fraude en línea, periodistas |
| W167 | 7–13 abr 2025 | política |
| W166 | 24–30 mar 2025 | Global Attitudes (EE. UU.) |
| W165 | 10–16 mar 2025 | marcas de medios, confianza social |
| W164 | 24 feb – 2 mar 2025 | ómnibus |
| W163 | 10–17 feb 2025 | tendencias sociales |
| W161 | 27 ene – 2 feb 2025 | política |
| W159 | 12–17 nov 2024 | poselectoral (incluye el voto de 2024) |

Pew publica los conjuntos de datos 12–18 meses después del trabajo de campo. Revisa las páginas de las olas W170 y
posteriores; una página que antes decía "not found" empezará a funcionar.

Los términos de Pew prohíben compartir los datos "in full or substantially in full" (completos o casi completos).
Guárdate los archivos; los puntajes y resúmenes que hagas a partir de ellos están bien.

## Actualizaciones

Quienes publican los datos sacan olas nuevas con nombres de archivo nuevos. Las descargas automáticas encuentran el
archivo actual en la página o la API de quien lo publica. Si una deja de funcionar porque quien la publica la movió,
descarga el archivo a mano en la carpeta de esa fuente y la página Datos lo encontrará. Los detalles técnicos de cada
fuente (URLs, nombres de variables, peculiaridades) están en `docs/data-sources-tech.md`.
