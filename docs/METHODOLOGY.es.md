# Cómo funciona Zócalo

Zócalo les hace preguntas a personas simuladas, interpretadas por modelos de lenguaje, y muestra las respuestas junto
con qué tan desviadas es probable que estén. Es una primera lectura rápida y barata de hacia dónde va una población.
**No sustituye encuestar a personas reales**, y esta página dice con claridad dónde se queda corto.

> **La prueba honesta.** En septiembre de 2026, Pew Research Center construyó un gemelo digital de cada persona de su
> propio panel, con su perfil real, 71 de sus actitudes reales y un modelo de frontera. En unas 300 preguntas, los
> gemelos se desviaron **12.4 puntos porcentuales** en promedio, y más de 15 puntos en el 28% de las preguntas. Todas
> las evaluaciones independientes que conocemos caen entre unos 10 y 20 puntos. Las cifras de precisión que destacan los
> proveedores suelen usar medidas en las que adivinar al azar ya saca buena calificación. El trabajo de Zócalo es superar
> referencias simples y decir qué tan desviado está, pregunta por pregunta.

## La versión corta

1. **Las personas** se toman de registros reales de censos y encuestas, en proporción a sus ponderaciones oficiales.
2. **Cada persona da una probabilidad para cada opción de respuesta**, no una sola elección. El resultado es el promedio
   de esas distribuciones.
3. **El orden de las opciones se revuelve para cada persona**, siempre se ofrece "No estoy seguro/a", y el modelo solo ve
   datos: ni nombre ni nada inventado.
4. **Cada número lleva un rango de error etiquetado**, tomado de resultados de pruebas medidos, nunca un margen de error
   de libro de texto.
5. **Las pruebas vienen incluidas.** Puedes medir el error tú mismo con datos reales de encuestas, y esas mediciones
   reemplazan las cifras publicadas con las que arranca la app.

## 1. Quiénes son las personas

Una población es un conjunto de registros de personas. Cada registro se escribe una vez y **nunca cambia**. Contiene:

- **Datos demográficos** de un registro real: edad, sexo, región, escolaridad, trabajo, rango de ingresos, raza o etnia,
  estado civil, hogar, religión, cuando la fuente los tiene.
- **Actitudes**, cuando una fuente las tiene: partido, ideología, último voto, religiosidad y algunas de las **propias
  respuestas anteriores** de la persona en encuestas ("opiniones").
- **Procedencia**: de qué archivo y de qué registro salió cada dato.

### Fuentes

| Fuente | Qué es una persona | De dónde vienen las actitudes |
|---|---|---|
| US Census ACS PUMS | Un registro real y anonimizado del censo | Emparejadas con un encuestado de CES (o GSS, o Pew) con el mismo rango de edad, sexo y nivel de escolaridad |
| UK Census 2021 teaching sample | Un registro real del censo (Inglaterra y Gales) | Emparejadas con encuestados de ESS o WVS del Reino Unido, si se descargaron |
| Canada 2021 Census PUMF | Un registro real del censo | Emparejadas con encuestados de WVS de Canadá, si se descargaron |
| CES, GSS, Pew ATP, WVS, ESS, Afrobarometer, Latinobarómetro, Arab Barometer | Un encuestado real | Sus propias respuestas |
| Demo | Una persona inventada a partir de proporciones redondeadas del país | Inventadas, y marcadas como **demo** en todas partes |

**Ponderación.** Las personas se toman en proporción a la ponderación de censo o de encuesta de cada registro (muestreo
ponderado sin reemplazo), así que una población se pondera sola y no necesita más reponderación. Si pides más personas
de las que tiene la encuesta de un país, algunos encuestados aparecen más de una vez, y la página de población lo dice.

**Rangos de edad.** Algunas fuentes solo dan un rango de edad (censo del Reino Unido, censo de Canadá, Pew). Entonces se
toma al azar una edad exacta dentro del rango, y la procedencia de la persona lo indica. Es el único valor que Zócalo
completa, y nunca sale del rango.

**Emparejar actitudes.** Un registro de censo no tiene opiniones. Zócalo le asigna el partido, la ideología, la religión
y las respuestas anteriores de un encuestado real que comparte su rango de edad, sexo y nivel de escolaridad. Esto
**agrega su propio error**: dos personas iguales en esas tres cosas pueden no estar de acuerdo. Nadie ha publicado
cuánto error agrega este emparejamiento, así que es una de las cosas que miden las pruebas.

**Lo que el modelo no puede hacer.** El modelo nunca inventa datos ni actitudes. Trabajos publicados encontraron que las
historias de vida más ricas, escritas por el modelo, empujan la opinión simulada hacia la izquierda: un estudio terminó
simulando que los demócratas ganaban todos los estados. Por eso Zócalo solo le da al modelo una lista de datos. **Los
nombres no se envían**, porque los nombres asociados a una identidad empujan a los modelos hacia estereotipos; los
nombres en la app son etiquetas de pantalla tomadas de listas por país.

### Ramas

Cualquier cambio a una persona (ajustar un rasgo para un "qué pasaría si", ver una noticia, una entrevista) es una
**rama** añadida sobre el registro base. La base nunca cambia, así que un panel se mantiene limpio de un estudio al
siguiente, y una persona a la que entrevistaste no lleva esa conversación a su siguiente encuesta.

## 2. Cómo responde una persona

Para cada pregunta, cada persona recibe una llamada al modelo. La llamada contiene los datos de la persona, la pregunta y
las opciones. **La persona da una probabilidad para cada opción** ("60% sí, 30% no, 10% no estoy seguro/a") y una razón
de una línea con su propia voz.

Por qué distribuciones y no respuestas únicas: varios estudios encontraron que pedirle al modelo una respuesta por
persona hace que todos elijan la misma opción. La dispersión de respuestas sale demasiado estrecha, y las opciones que
eligen las personas reales nunca aparecen. Pedir una distribución de probabilidades redujo ese error alrededor de
35–50% en tres estudios independientes (Jang et al. 2026; Meister et al. 2024; Prolific 2026). El muestreo repetido y
las probabilidades crudas de tokens funcionaron peor.

Reglas que se aplican a cada llamada:

- **El orden de las opciones se revuelve por persona.** En las escalas ("muy de acuerdo" a "muy en desacuerdo") el orden
  se invierte al azar, para que la escala siga en orden. Si no, los modelos tienen sesgos fuertes de posición y de
  etiqueta.
- **Siempre se ofrece "No estoy seguro/a", al final.** Las personas reales dicen "no estoy seguro/a" unas cuatro veces
  más seguido que las simuladas.
- **La instrucción pide la respuesta de esta persona**: no la de un experto, ni más positiva o más negativa, más amable
  o más complaciente de lo que sería.
- **La temperatura se deja en el valor predeterminado del proveedor.** Subirla no arregla respuestas demasiado
  parecidas.

**Opción de palabras propias.** Para escalas e intención de compra puedes elegir *palabras propias → opciones*: la
persona responde con una oración, y una llamada aparte y neutral al modelo asigna esas palabras a las opciones como
probabilidades. Esto sigue la idea de la calificación por similitud semántica (Maier et al. 2025), que usaba embeddings
de texto para la asignación. Zócalo usa en cambio una llamada de juez, así que tómalo como una opción por probar, no
como una mejora comprobada.

**Varios modelos.** Elige más de un modelo y cada uno le pregunta a cada persona. Los resultados muestran los modelos
juntos (las distribuciones de cada persona se promedian entre modelos) y por separado. Pew encontró que un modelo de
frontera muestra al público como demasiado extremo y otro como demasiado moderado, así que mezclarlos podría ayudar.
Eso no se ha probado, así que las pruebas comparan una mezcla contra modelos individuales.

## 3. Tipos de estudio

**Encuesta.** Todos responden todas las preguntas. Las preguntas se hacen por separado, así que ninguna respuesta ve
otra.

**Prueba A/B.** Las personas se dividen en **mitades equivalentes**: se ordenan en grupos por rango de edad, sexo, región
y escolaridad, se revuelven dentro de cada grupo y luego se reparten de forma alternada. La mitad A ve la versión A de
cada pregunta (y, si quieres, un texto para leer primero), la mitad B ve la versión B. El resultado es B menos A.

**Prueba de noticia (tratamiento informativo).** "¿Comprarías Y a $X?", después de leer una noticia. Las personas se
dividen en **tercios equivalentes**:

- **control:** sin noticia
- **tratamiento:** la noticia
- **placebo:** una noticia neutral de largo similar

**El efecto que se muestra es tratamiento menos placebo, nunca el cambio bruto.** Los modelos reaccionan a que les
muestren *cualquier cosa*; el placebo mide esa reacción, para poder restarla. Opcionalmente, un **grupo de las mismas
personas** también responde, lee la noticia y vuelve a responder en la misma conversación. Así es como la gente suele
hacer estas pruebas a mano, y exagera los efectos, porque que te pregunten dos veces indica que la respuesta debería
cambiar. La diferencia entre los dos diseños muestra cuánto. También puedes decirle al modelo que está en un
experimento, lo que redujo la sobrerreacción en un estudio.

Evidencia publicada: los modelos suelen acertar la **dirección** de un efecto pero **exageran su tamaño** (Hewitt et al.
2024: r = 0.85 entre efectos predichos y reales, con tamaños sistemáticamente demasiado grandes), y reaccionan a cambios
que las personas ignoran (Tjuatja et al. 2024). Lee los resultados de las pruebas de noticia como dirección, no como
tamaño.

**Grupos focales y debates.** Unas cuantas personas y tú, el moderador; o dos personas con posturas fijas. Los grupos
simulados llegan a un acuerdo total mucho más seguido que los reales (85–96% contra 51% en un estudio). Por eso cada
debate primero le hace la pregunta a cada lado a solas (la "rama sin discusión") y otra vez al final, y muestra cuánto
se movió cada uno. **Nunca tomes un consenso simulado como pronóstico.** En conversaciones largas, los personajes también
regresan a la voz predeterminada del modelo, en unos 8 turnos según un estudio. Zócalo repite los datos de cada persona
en cada turno, conserva los turnos recientes más un resumen, y cada 10 turnos vuelve a preguntar discretamente una de
las respuestas registradas de la persona para revisar la deriva.

## 4. Cómo se estima y se muestra el error

Cada número en Zócalo lleva un rango de error, etiquetado con **qué tipo** de estimación es:

| Etiqueta | Significado |
|---|---|
| **medido en tus pruebas** | El error para este tipo de pregunta, medido por tus propias corridas de prueba (20+ preguntas de ese tipo) |
| **estimación de evaluaciones publicadas** | Hasta que tus pruebas cubran un tipo de pregunta, cifras de evaluaciones publicadas |
| **estimación fija** | El tipo de pregunta es "otra": el error general entre tipos, no específico de esta pregunta |
| **calibrado con humanos** | Un intervalo de confianza real del 95%, porque agregaste una muestra humana real (sección 5) |

Se muestra como **"por lo general dentro de ±a puntos, 1 de cada 5 veces más de ±b"**: la mediana y el percentil 80 del
error absoluto por opción de respuesta.

**Los tipos de pregunta** definen el error: *opinión*, *comportamiento*, *consumo/precio* y *conocimiento*, cada uno ya
sea atemporal o sobre noticias recientes. Zócalo adivina el tipo por la redacción, y tú puedes cambiarlo. Cifras
iniciales, en puntos porcentuales:

| Tipo | Típico | 1 de cada 5 supera | Fuentes principales |
|---|---|---|---|
| Opinión | 7 | 15 | Pew 2026; Verasight 2025 (unos 4 en resultados políticos generales comunes) |
| Opinión, de actualidad | 10 | 22 | Pew 2026 ("ha oído mucho sobre centros de datos": 3% simulado vs 25% real) |
| Comportamiento | 9 | 18 | Pew 2026 |
| Consumo / precio | 12 | 25 | Verasight 2025 (19.8 en preguntas de consumo); Harris/AAPOR 2024 |
| Conocimiento / conciencia | 18 | 40 | Pew 2026 (+43 a +46 en reactivos de conocimiento) |
| Otra (fija) | 12 | 25 | Todas las anteriores |

**Ajustes.**

- **Los subgrupos** reciben un error mayor: ×1.3, y más para grupos pequeños. Los subgrupos simulados se equivocan más
  que el total (Pew: 16.1 para republicanos y 15.1 para adultos negros contra 12.4 en general), y las brechas entre
  segmentos se exageran 2–4× (Chen et al. 2026).
- **Fuera de EE. UU.**, los errores se amplían 25% hasta que se prueben, porque casi toda la evidencia publicada es
  estadounidense.
- **Las poblaciones de demostración** llevan una advertencia de que son inventadas.

**Nunca un margen de error de muestreo.** El típico "±3% para 1,000 personas" de libro de texto no aparece en ningún
lado. Mide el ruido del muestreo aleatorio, y agregar personas simuladas no hace nada contra el sesgo propio del modelo,
que es el error más grande.

**¿Se cumplen los rangos?** Cada corrida de prueba registra qué tan seguido el error real quedó dentro del rango de 1 de
cada 5 mostrado. Debería ser cerca del 80%. Esta cifra de "rangos que se cumplieron" está en la página Pruebas. Tiene más
sentido con olas de encuestas publicadas después de la fecha de corte de entrenamiento del modelo, porque las encuestas
más antiguas pueden estar memorizadas.

**Sin pruebas de significancia con datos simulados.** Las respuestas simuladas varían mucho menos que las reales
(demasiado estrechas en 154 de 164 resultados en un estudio grande), así que los valores p calculados con ellas estarían
mal. Zócalo no reporta ninguno, salvo con una muestra humana.

## 5. Calibración

1. **Ponderación.** Se hace tomando a las personas en proporción a sus ponderaciones (sección 1). Es higiene básica, no
   una solución: Pew ponderó a sus gemelos y aun así se desvió 12 puntos.
2. **Encuestas reales más parecidas (anclas).** Cuando descargas una encuesta de opinión, Zócalo indexa sus preguntas y
   sus proporciones de respuesta reales y ponderadas por país. Una pregunta nueva se empareja con sus preguntas reales
   más parecidas por similitud de palabras (TF-IDF), y esas se muestran junto a tus resultados. **Las anclas se muestran,
   no se aplican**: no se sabe si ayuda mover las respuestas simuladas hacia la encuesta real más cercana, y la
   referencia *anchor* de las pruebas mide qué tan bien predice la encuesta más cercana por sí sola. La similitud
   también decide si una pregunta cuenta como "cercana" a datos reales.
3. **Corrección con muestra humana (prediction-powered inference).** Sube respuestas reales a la misma pregunta de una
   muestra humana pequeña, con datos demográficos si los tienes. Cada persona real se empareja con la persona simulada
   más parecida. La diferencia promedio entre respuestas reales y simuladas corrige el resultado simulado, y las barras
   de error se vuelven un intervalo de confianza real del 95% (Broska et al. 2025; Zhang et al. 2025 encontraron que
   alrededor de 10% de datos humanos corregía las estimaciones de demanda). Es la única vía hacia resultados
   estadísticamente válidos. Sin ella, lee los resultados como dirección.

## 6. Las pruebas

La página Pruebas usa la misma maquinaria con preguntas cuyas respuestas reales se conocen:

| Conjunto de prueba | Qué revisa |
|---|---|
| **Gemelos de encuestados** (Pew, GSS, WVS, ESS, Afrobarometer, Latinobarómetro, Arab Barometer) | Al estilo de Pew: cada persona simulada es gemela de un encuestado real (datos demográficos más algunas de sus *otras* respuestas); la respuesta real es el resultado ponderado de la propia encuesta |
| **Twin-2K-500** | Gemelos de 2,058 personas construidos con sus respuestas de las olas 1–3, que predicen sus respuestas de la ola 4. También mide la precisión individual |
| **GlobalOpinionQA** | Preguntas de Pew Global Attitudes y WVS, con las proporciones reales de cada país |
| **SimBench** | Preguntas de 20 encuestas y experimentos |

Cada prueba se puede correr con el método real o con una referencia:

| Método | Qué es |
|---|---|
| **Personas simuladas** | El método de Zócalo |
| **Pedir las proporciones** | Se le piden al modelo directamente las proporciones de respuesta del país, sin personas |
| **La otra encuesta real más parecida** | Las proporciones de respuesta reales de la *otra* pregunta más parecida en el índice |
| **Todas las opciones iguales** | Un reparto uniforme |
| **Encuestados reales parecidos** | Sin IA: cada persona de prueba recibe las respuestas de los 25 otros encuestados más parecidos (solo pruebas de gemelos) |

La referencia sin IA importa. Un estudio de 2026 encontró que ningún modelo de lenguaje superó a la mejor referencia sin
IA al predecir individuos (Chen et al. 2026). Ve las respuestas reales de otros encuestados a la misma pregunta, así que
su error *general* es un tope para preguntas que ya se hicieron, no un rival justo. Su *precisión individual* es la
comparación justa. Si Zócalo no puede superar las referencias uniforme y "pedir las proporciones" en tu tipo de
pregunta, sus respuestas no están aportando nada. Si no se acerca a "encuestados parecidos" en individuos, es lo
esperado: hasta ahora ningún modelo lo hace.

**Primeros resultados en esta instalación (noviembre de 2026, Gemini 3.1 Flash-Lite, 20 personas por pregunta; muestras
pequeñas).**

| Prueba | Personas simuladas | Uniforme | La otra encuesta más parecida | Encuestados parecidos (sin IA) |
|---|---|---|---|---|
| Latinobarómetro 2024, México, 8 preguntas | 18.5 pts de media (11.5 de mediana); precisión individual 59% | 27.1 pts | 9.5 pts (5 preguntas) | precisión individual 71% |
| Twin-2K-500, 6 preguntas | 17.7 pts de media (13.2 de mediana); precisión individual 36% | — | — | precisión individual 45% |

Coinciden con el rango publicado (unos 10–20 puntos). Los rangos de error iniciales se cumplieron en 62–67% de las
preguntas en vez de 80%, así que fueron demasiado optimistas para estos conjuntos. Los valores medidos los reemplazan a
medida que se acumulan pruebas.

**Medidas.**

- **Error absoluto medio por pregunta**, en puntos, entre las opciones de respuesta.
- **Proporción de preguntas con una opción desviada más de 15 puntos.**
- **Opciones que eligieron personas reales (5% o más) y que la simulación casi nunca eligió** (menos de 1%).
- **Razón de dispersión** en escalas: simulada entre real. Menos de 1 significa respuestas demasiado amontonadas.
- **Precisión individual** para gemelos.
- **Rangos que se cumplieron** (sección 4).

Los resultados por tipo de pregunta reemplazan las cifras iniciales publicadas una vez que se prueban 20 o más preguntas
de un tipo.

**Memorización.** Las encuestas famosas y antiguas pueden estar en los datos de entrenamiento de un modelo, lo que
favorece a todos los métodos. Prefiere olas de encuestas levantadas después de la fecha de corte de entrenamiento del
modelo. La página Datos explica cómo agregar las olas más recientes de Pew.

## 7. Fallas conocidas

Ordenadas según cuánto afectan, a partir de la evidencia publicada (fuentes en `docs/research.md`):

1. **Subgrupos estereotipados.** Las mayorías se vuelven casi unánimes (Pew: 97% simulado contra 43% real en el interés
   de adultos hispanos por el Mundial), y las brechas entre segmentos salen 2–4× demasiado grandes. Los resultados de
   subgrupos reciben rangos de error mayores y una advertencia.
2. **Respuestas demasiado parecidas.** Distribuciones demasiado estrechas y opciones reales que nunca se eligen, así que
   los valores p no serían válidos. Se atiende con probabilidades declaradas, "No estoy seguro/a" y una revisión en cada
   resultado de las opciones que casi nadie eligió. Aun así, las respuestas siguen siendo demasiado parecidas, así que no
   se muestran pruebas de significancia.
3. **Un buen resultado general que esconde subgrupos y temas nuevos malos.** Los errores de subgrupos y de actualidad se
   etiquetan por separado.
4. **Efectos de tratamiento inflados.** Brazos de placebo, y una nota de que la dirección es más confiable que el tamaño.
5. **Preguntas de conocimiento respondidas demasiado bien.** Las preguntas de "¿has oído hablar de…" reciben la etiqueta
   de conocimiento, los errores más amplios y una advertencia.
6. **Historias de vida inventadas que se inclinan a la izquierda.** El modelo nunca inventa datos.
7. **Positividad y deseabilidad social.** La instrucción pide la respuesta real de esta persona; los resultados de
   consumo se marcan como direccionales salvo que se calibren con una muestra humana.
8. **Artefactos de posición, etiqueta y redacción, y deriva del modelo.** Las opciones se revuelven, las versiones del
   modelo se fijan a lo que elegiste, y cada respuesta registra el modelo, el orden de las opciones, la huella de la
   instrucción y la semilla.
9. **Grupos que se ponen de acuerdo demasiado fácil, y personajes que derivan.** Ramas sin discusión, datos repetidos y
   revisiones de deriva.
10. **Validación complaciente.** Referencias, error medido por tipo de pregunta y "rangos que se cumplieron".

## 8. Lo que aún no sabemos

Esto no tiene evidencia publicada. Tus corridas de prueba son la forma de averiguarlo:

- Cuánto error agrega el emparejamiento de actitudes (registro de censo + encuestado) comparado con las propias
  respuestas de una persona.
- Si anclar a la encuesta real más cercana mejora las preguntas nuevas o de actualidad.
- Si mezclar modelos supera al mejor modelo individual.
- Cuánto infla los efectos el diseño de las mismas personas, y si la reacción al placebo lo predice.
- Si las ramas mantienen a los gemelos más fieles que una sola conversación larga.
- Qué tan bien funciona todo esto fuera de EE. UU., y en preguntas de consumo más allá de categorías de un solo
  producto.
- Qué tan estables son los resultados entre versiones de modelos a lo largo de los meses.

## 9. Reproducibilidad

Cada respuesta se guarda con:

- la persona y la rama;
- el brazo;
- el modelo;
- el orden de las opciones mostrado;
- una huella de la instrucción exacta;
- la semilla del estudio;
- los conteos de tokens y el costo.

Duplica un estudio para volver a correrlo. Cambiar el modelo lo convierte en otro estudio: en trabajos publicados los
resultados han derivado en menos de tres meses, así que compara corridas solo con la misma versión del modelo.

## 10. Datos y licencias

Zócalo nunca incluye datos de encuestas. La página Datos descarga cada archivo de quien lo publica, o explica cómo
conseguirlo cuando quien lo publica te pide iniciar sesión o llenar un formulario. Cada fuente conserva su propia
licencia. Algunas solo permiten uso no comercial (WVS, ESS, Latinobarómetro, GlobalOpinionQA, SimBench), y un ajuste las
desactiva para uso comercial. Cualquier cosa que publiques derivada de una fuente, como puntajes o pesos ajustados
(fine-tuned), hereda los términos de esa fuente. Los modelos reciben el perfil de una persona a la vez, nunca conjuntos
de datos completos.
