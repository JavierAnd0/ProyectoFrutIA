// Genera FruitAI_documento.docx: el documento original (corregido) + las secciones nuevas.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, LevelFormat, TableOfContents, PageBreak,
  Footer, PageNumber, HighlightColor,
} = require("docx");

const FUENTE = "Times New Roman";
const ANCHO = 9360; // carta con márgenes de 1": 12240 - 2*1440

// ---------- texto con marcas simples ----------
// **negrita**, *cursiva*, `código`, [PENDIENTE: ...] resaltado
function runs(texto, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[PENDIENTE:[^\]]+\])/g;
  let i = 0, m;
  while ((m = re.exec(texto))) {
    if (m.index > i) out.push(new TextRun({ text: texto.slice(i, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Courier New", size: 20, ...base }));
    else if (t.startsWith("[PENDIENTE")) out.push(new TextRun({ text: t, shading: { type: ShadingType.CLEAR, fill: "FFF2A8", color: "auto" }, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    i = m.index + t.length;
  }
  if (i < texto.length) out.push(new TextRun({ text: texto.slice(i), ...base }));
  return out;
}
const P = (t, op = {}) => new Paragraph({ children: runs(t), alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 300 }, ...op });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const VIN = (t) => new Paragraph({ numbering: { reference: "vinetas", level: 0 }, children: runs(t), alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 276 } });
const NUM = (ref, t) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 276 } });
const ETQ = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true })], spacing: { before: 120, after: 60 }, keepNext: true });
const NOTA = (t) => new Paragraph({ children: runs(t, { italics: true, size: 21 }), spacing: { after: 120 }, indent: { left: 360 } });
const PEND = (t) => new Paragraph({ children: [new TextRun({ text: t, shading: { type: ShadingType.CLEAR, fill: "FFF2A8", color: "auto" } })], spacing: { after: 120 } });

let nFig = 0, nTab = 0;
function figura(archivo, ancho, alto, titulo) {
  nFig++;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(archivo), transformation: { width: ancho, height: alto },
        altText: { title: titulo, description: titulo, name: titulo } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Figura ${nFig}. `, bold: true, italics: true, size: 20 }), new TextRun({ text: titulo, italics: true, size: 20 })] }),
  ];
}
function figuraPendiente(titulo) {
  nFig++;
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 200 },
    children: [new TextRun({ text: `[Figura ${nFig}: ${titulo}]`, shading: { type: ShadingType.CLEAR, fill: "FFF2A8", color: "auto" }, italics: true, size: 20 })] });
}

const borde = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
function tabla(titulo, cab, filas, anchos) {
  nTab++;
  const total = anchos.reduce((a, b) => a + b, 0);
  const celda = (t, i, esCab) => new TableCell({
    width: { size: anchos[i], type: WidthType.DXA }, borders: bordes,
    shading: esCab ? { fill: "D9E2F3", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: runs(t, { size: 20, bold: esCab || undefined }) })],
  });
  return [
    new Paragraph({ keepNext: true, spacing: { before: 160, after: 80 },
      children: [new TextRun({ text: `Tabla ${nTab}. `, bold: true, italics: true, size: 20 }), new TextRun({ text: titulo, italics: true, size: 20 })] }),
    new Table({
      width: { size: total, type: WidthType.DXA }, columnWidths: anchos,
      rows: [new TableRow({ tableHeader: true, children: cab.map((t, i) => celda(t, i, true)) }),
        ...filas.map((f) => new TableRow({ children: f.map((t, i) => celda(t, i, false)) }))],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}
const REF = (t) => new Paragraph({ children: runs(t), indent: { left: 720, hanging: 720 }, spacing: { after: 100, line: 276 } });

// =====================================================================
const c = [];

// ---------- Portada ----------
c.push(new Paragraph({ spacing: { before: 2400, after: 240 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "FruitAI", bold: true, size: 56 })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [new TextRun({ text: "Control de inventario de frutas con TinyML, Home Assistant y un agente de IA local", size: 30 })] }));
for (const t of ["[Autor]", "[Programa / curso]", "[Institución]", "[Fecha]"])
  c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: t, size: 24 })] }));
c.push(new Paragraph({ children: [new PageBreak()] }));

// ---------- Índice ----------
c.push(new Paragraph({ children: [new TextRun({ text: "Contenido", bold: true, size: 28 })], spacing: { after: 200 } }));
c.push(new TableOfContents("Contenido", { hyperlink: true, headingStyleRange: "1-2" }));
c.push(new Paragraph({ children: [new TextRun({ text: "(Si el índice aparece vacío: clic derecho sobre él → Actualizar campo.)", italics: true, size: 18, color: "777777" })] }));
c.push(new Paragraph({ children: [new PageBreak()] }));

// ---------- 1. Introducción ----------
c.push(H1("1. Introducción"));
c.push(P("El control de inventario de alimentos en hogares y negocios locales se realiza de forma manual o no se realiza, lo cual dificulta saber qué hay disponible o qué productos se consumen con mayor frecuencia. Por otra parte, los microcontroladores actuales permiten ejecutar modelos de aprendizaje automático directamente en el dispositivo, y plataformas de código abierto como Home Assistant facilitan integrar sensores, automatizaciones y asistentes de voz o texto."));
c.push(P("FruitAI une estas piezas de bajo costo en un mismo ecosistema para que el usuario pueda interactuar con el inventario de una forma innovadora: mediante un agente de IA local responde preguntas como «¿cuántas manzanas quedan?» o «¿cuántos bananos se consumieron esta semana?»."));
c.push(P("En este documento se describen el problema abordado, la arquitectura del sistema, el proceso de desarrollo, las pruebas realizadas y las conclusiones obtenidas."));

// ---------- 2. Problema ----------
c.push(H1("2. Problema"));
c.push(P("Llevar el registro de las frutas disponibles supone un inconveniente según la escala y las necesidades de cada caso: anotar cada compra y cada consumo es tedioso, y lo que queda se desconoce hasta que se revisa físicamente."));
c.push(P("Se plantea entonces la siguiente pregunta: ¿cómo construir, con hardware de bajo costo y procesamiento local, un sistema que identifique frutas, registre sus entradas y salidas de forma confiable y permita consultar el inventario en lenguaje natural?"));
c.push(P("Para resolverlo se propone utilizar la cámara del ESP32-S3 para identificar una fruta y luego registrar explícitamente una entrada o una salida del inventario. El inventario no debe cambiar después de cada predicción de la cámara, ya que la misma fruta puede permanecer visible durante varios fotogramas."));

// ---------- 3. Objetivos ----------
c.push(H1("3. Objetivos"));
c.push(H2("3.1 Objetivo general"));
c.push(P("Desarrollar un prototipo de control de inventario de frutas que integre un modelo TinyML ejecutado en hardware de bajo costo (ESP32-S3 y Raspberry Pi), Home Assistant, una base de datos y un agente de IA local, capaz de registrar entradas y salidas y de responder consultas en lenguaje natural."));
c.push(H2("3.2 Objetivos específicos"));
for (const t of [
  "Entrenar y desplegar en el ESP32-S3 un modelo de clasificación de imágenes que reconozca varios tipos de fruta.",
  "Implementar una lógica de confirmación que evite registros duplicados a partir de predicciones consecutivas.",
  "Integrar el dispositivo con Home Assistant mediante MQTT para mantener el inventario actualizado y visible en un panel.",
  "Diseñar e implementar una base de datos que almacene el historial de movimientos.",
  "Configurar un agente de IA local que responda preguntas sobre el inventario y su historial.",
  "Evaluar el desempeño del sistema mediante pruebas con movimientos reales.",
]) c.push(NUM("objetivos", t));

// ---------- 4. Alcance ----------
c.push(H1("4. Alcance y limitaciones"));
c.push(ETQ("Incluido en el alcance:"));
for (const t of [
  "Clasificación de manzanas (rojas y verdes), peras, bananos y kiwis, más una clase «fondo», una fruta a la vez.",
  "Registro explícito de entradas y salidas desde el panel de Home Assistant (botones Entrada y Salida), con la fruta reconocida por la cámara.",
  "Visualización de la cámara del ESP32-S3 en el panel.",
  "Inventario y panel en Home Assistant, con acceso desde la aplicación móvil.",
  "Base de datos SQLite con el historial de movimientos.",
  "Agente conversacional local (Ollama + Assist) para consultas de inventario e historial.",
]) c.push(VIN(t));
c.push(ETQ("Fuera del alcance:"));
for (const t of [
  "Pronóstico de consumo, que requiere un historial de varias semanas.",
  "Detección de madurez o daño en la fruta.",
  "Reconocimiento de varias frutas simultáneamente.",
  "Uso en condiciones de iluminación no controladas.",
  "Estación física con pulsadores, sensor de presencia y sensor de temperatura y humedad: quedó diseñada y programada, pero se deja como mejora futura (sección 9.1).",
]) c.push(VIN(t));
c.push(ETQ("Limitaciones:"));
for (const t of [
  "Tiempo de desarrollo y disponibilidad de sensores: la versión actual usa solo la Raspberry Pi y el ESP32-S3 con cámara.",
  "Conjunto de datos: pocas fotos propias por clase; la pera y el kiwi solo cuentan con imágenes de Fruits-360.",
  "El modelo funciona en el montaje para el que se entrenó (fondo y luz fijos).",
  "El agente de IA local depende de que el equipo esté encendido.",
]) c.push(VIN(t));

// ---------- 5. Marco digital ----------
c.push(H1("5. Marco digital"));
const def = (t, d) => P(`**${t}.** ${d}`);
c.push(def("TinyML", "Rama del aprendizaje automático enfocada en ejecutar modelos en microcontroladores con pocos recursos de memoria y energía. Permite la inferencia local, sin enviar imágenes a la nube, con baja latencia y mayor privacidad (Warden y Situnayake, 2019)."));
c.push(def("Clasificación de imágenes", "Tarea en la que un modelo asigna una etiqueta a una imagen completa. Se eligió clasificación, y no detección de objetos, porque el sistema procesa una fruta a la vez frente a una cámara fija: basta con decidir qué fruta hay (o si no hay ninguna), sin ubicarla dentro de la imagen. Los modelos de detección (por ejemplo YOLO o FOMO) requieren más memoria y un etiquetado más costoso, con un recuadro por objeto en cada foto."));
c.push(def("Aprendizaje por transferencia", "Técnica que reutiliza una red neuronal ya entrenada con un conjunto grande y general de imágenes (ImageNet) y reentrena solo su parte final con las clases del problema. La red ya reconoce bordes, colores, texturas y formas, por lo que bastan unos cientos de fotos por clase en lugar de miles."));
c.push(def("MobileNet", "Familia de redes convolucionales diseñadas para dispositivos con pocos recursos, basadas en convoluciones separables en profundidad (*depthwise separable*), que reducen el número de operaciones y parámetros (Howard et al., 2017; Sandler et al., 2018). El multiplicador de ancho α reduce el número de filtros de cada capa: con α = 0,25 la red tiene cerca de la cuarta parte de los canales de la versión completa."));
c.push(def("Cuantización", "Representación de los pesos y las activaciones de la red con enteros de 8 bits (int8) en lugar de números de punto flotante de 32 bits. El modelo ocupa unas cuatro veces menos memoria y se ejecuta más rápido en microcontroladores con instrucciones para enteros, como el ESP32-S3. Puede hacerse después de entrenar (*post-training quantization*, PTQ) o simulándola durante el entrenamiento (*quantization-aware training*, QAT), lo que permite al modelo adaptarse al redondeo (Jacob et al., 2018; Krishnamoorthi, 2018)."));
c.push(def("Edge Impulse", "Plataforma en línea para crear modelos de TinyML: carga y etiquetado de datos, entrenamiento, estimación del rendimiento en el dispositivo y exportación del modelo como librería para Arduino (Hymel et al., 2022)."));
c.push(def("ESP32-S3", "Microcontrolador de doble núcleo a 240 MHz con Wi-Fi, instrucciones vectoriales que aceleran las operaciones de redes neuronales y soporte para memoria PSRAM externa. Las placas usadas incluyen una cámara OV2640."));
c.push(def("MQTT", "Protocolo de mensajería ligero de tipo publicación/suscripción, muy usado en Internet de las Cosas (OASIS, 2014). Los dispositivos publican mensajes en *tópicos* y un intermediario (*broker*, en este caso Mosquitto) los entrega a quienes estén suscritos. En el proyecto se usan los niveles de calidad de servicio (QoS), los mensajes retenidos (*retain*), para que el último valor quede disponible, y el mensaje de «última voluntad» (*Last Will and Testament*, LWT), que el broker publica si un dispositivo se desconecta sin avisar."));
c.push(def("Home Assistant", "Plataforma de código abierto para automatización del hogar. Integra dispositivos (en este proyecto por MQTT), muestra paneles, ejecuta automatizaciones y ofrece el asistente conversacional Assist, que interpreta frases con *oraciones locales* (patrones definidos por el usuario) o delega en un modelo de lenguaje."));
c.push(def("Modelo de lenguaje local", "Modelo de lenguaje (LLM) que se ejecuta en un equipo propio, sin enviar datos a servicios en la nube. Se usó Ollama para servir el modelo Qwen 2.5 de 3 000 millones de parámetros (Qwen Team, 2024)."));
c.push(def("Docker", "Herramienta que ejecuta aplicaciones en contenedores aislados. Permite que el mismo sistema funcione igual en un computador portátil y en la Raspberry Pi."));
c.push(def("SQLite", "Base de datos relacional contenida en un solo archivo, sin servidor, adecuada para un dispositivo como la Raspberry Pi."));

// ---------- 6. Arquitectura ----------
c.push(H1("6. Arquitectura del sistema"));
c.push(P("FruitAI se compone de tres partes: el ESP32-S3 con cámara, un servidor en la Raspberry Pi y la aplicación de Home Assistant en el celular, desde donde se opera todo el sistema (Figura 1)."));
c.push(...figura("arquitectura.png", 600, 276, "Arquitectura de FruitAI."));
c.push(H2("6.1 ESP32-S3 con cámara"));
c.push(P("El ESP32-S3 va fijo, mirando hacia abajo a una superficie de fondo claro y con luz pareja. El modelo TinyML clasifica cada fotograma en el propio ESP32 y la lógica de confirmación decide cuándo una fruta está confirmada. El ESP32 informa a Home Assistant qué fruta tiene confirmada y envía unas dos fotos por segundo para ver la cámara en el panel; el reconocimiento se hace siempre en el ESP32. El envío de fotos se puede desactivar, y entonces ninguna imagen sale del dispositivo."));
c.push(H2("6.2 Servidor (Raspberry Pi con Docker)"));
c.push(...tabla("Contenedores del servidor.", ["Contenedor", "Función"], [
  ["Mosquitto", "Broker MQTT; un usuario y contraseña por cliente (ESP32, servicio, Home Assistant)."],
  ["Servicio (Python)", "Único componente que escribe en la base de datos y calcula el stock y los resúmenes."],
  ["Home Assistant", "Panel, notificaciones, registro desde el panel y asistente Assist."],
  ["Ollama", "Modelo de lenguaje local para las preguntas abiertas."],
], [2400, 6960]));
c.push(P("La Figura 2 muestra qué se ejecuta en cada equipo y por qué protocolo se comunican."));
c.push(...figura("despliegue.png", 600, 318, "Diagrama de despliegue (nodos, contenedores y protocolos)."));
c.push(H2("6.3 Flujo de un registro"));
for (const t of [
  "El ESP32 confirma la fruta (sección 7.2) y la muestra en el panel como «Fruta detectada». El usuario pulsa Entrada en el panel y Home Assistant envía la orden al ESP32 por MQTT.",
  "El ESP32 publica en el tópico `fruitai/movimiento` un mensaje JSON con la fruta, el tipo, la cantidad, la confianza y un identificador único del evento (`evento_id`).",
  "El servicio valida el mensaje, lo guarda en SQLite con la hora de recepción y recalcula el stock. Si el `evento_id` ya existe, lo ignora (un mensaje con QoS 1 puede llegar dos veces). Si es una salida sin stock, la rechaza y publica un aviso en `fruitai/aviso`.",
  "El servicio publica el stock y los resúmenes (salidas de hoy y de la semana) como mensajes retenidos.",
  "Home Assistant crea los sensores automáticamente por *MQTT discovery* y actualiza el panel.",
]) c.push(NUM("flujo", t));
c.push(P("La orden se procesa en el ESP32 y no en Home Assistant: así la lógica anti-duplicados se aplica siempre en el mismo lugar. Si la orden se ignora (no hay fruta confirmada o ya se registró), el ESP32 publica el motivo y llega como notificación al celular. Los botones del panel aparecen deshabilitados cuando el ESP32 está desconectado."));
c.push(H2("6.4 Base de datos"));
c.push(P("Tabla de frutas, tabla de movimientos (fruta, tipo, cantidad, confianza, fecha y `evento_id` único) y tabla de lecturas de ambiente. El stock no se guarda: se calcula siempre a partir de los movimientos, de modo que el historial es la única fuente de verdad."));
c.push(H2("6.5 Consultas en lenguaje natural"));
c.push(P("Las preguntas frecuentes («¿cuántas peras hay?», «¿cuántos bananos salieron esta semana?») se resuelven con oraciones locales de Assist: responden al instante y siempre con el valor exacto del sensor. Las preguntas que no encajan en esos patrones («¿qué fruta se está acabando?») pasan al modelo de lenguaje. A este se le entregan en las instrucciones los datos actuales del inventario con los totales y las comparaciones ya calculados, porque un modelo pequeño se equivoca al sumar o comparar."));
c.push(H2("6.6 Acceso remoto y seguridad"));
c.push(P("La aplicación del celular se conecta mediante Tailscale, una red privada que publica Home Assistant con HTTPS solo para los dispositivos del usuario. El puerto de Ollama, que no tiene autenticación, se publica únicamente en el propio equipo, y las credenciales (claves MQTT, token de Home Assistant, Wi-Fi del ESP32) se mantienen fuera del repositorio."));

// ---------- 7. Desarrollo ----------
c.push(H1("7. Desarrollo"));
c.push(H2("7.1 Metodología"));
c.push(P("El desarrollo fue incremental y en paralelo a la llegada del hardware. Como al inicio no se contaba con el ESP32-S3 ni con la Raspberry Pi, cada parte se construyó primero en un computador portátil con Docker, que ejecuta las mismas imágenes que usará la Raspberry Pi, y el ESP32 se reemplazó por dos simuladores que publican exactamente los mismos mensajes MQTT:"));
c.push(VIN("un simulador por línea de comandos para generar movimientos de prueba, y"));
c.push(VIN("un «ESP32 virtual» que usa la cámara del computador, el mismo modelo exportado y la misma lógica de confirmación que el firmware."));
c.push(P("Así, el servicio, la base de datos, Home Assistant y el agente se probaron de extremo a extremo antes de tener el hardware, y el firmware solo cambia la fuente de las imágenes y de los botones."));
c.push(H2("7.2 Lógica de confirmación anti-duplicados"));
c.push(P("La cámara clasifica unas cinco imágenes por segundo y la misma fruta permanece visible durante muchos fotogramas, por lo que el inventario no puede cambiar con cada predicción. Se implementó una máquina de estados (Figura 3):"));
c.push(...figura("estados.png", 600, 204, "Máquina de estados de la lógica de confirmación."));
for (const t of [
  "**ESPERANDO → CONFIRMADA:** una fruta queda confirmada cuando el modelo la predice durante 5 fotogramas seguidos (≈ 1 s) con confianza ≥ 0,75. Si cambia la predicción o baja la confianza, el conteo se reinicia.",
  "**CONFIRMADA → REGISTRADA:** solo con una fruta confirmada, la orden Entrada o Salida genera **un** movimiento. Sin fruta confirmada, la orden se ignora.",
  "**REGISTRADA → ESPERANDO:** después del registro, nuevas órdenes se ignoran hasta que la fruta se retire, es decir, hasta que la cámara vea «fondo» durante 5 fotogramas.",
]) c.push(NUM("estados", t));
c.push(P("Las manzanas roja y verde son clases distintas del modelo, pero se registran como la misma fruta del inventario («manzana»). La lógica se escribió primero en Python (para el ESP32 virtual) y se tradujo línea por línea a C++ para el firmware; ambas versiones pasan el mismo conjunto de pruebas."));
c.push(H2("7.3 Conjunto de datos"));
c.push(...tabla("Conjunto de datos de entrenamiento.", ["Fuente", "Clases", "Imágenes activas"], [
  ["Fruits-360 (Mureșan y Oltean, 2018; CC BY-SA 4.0), 100 × 100 px, fondo blanco", "banano, kiwi, manzana roja, manzana verde, pera", "150 por clase (60 en manzana verde)"],
  ["Fotos propias en el montaje, cámara del computador", "banano (51), fondo (71), manzana roja (40), manzana verde (169)", "331"],
  ["**Total**", "6 clases", "**991**"],
], [3900, 3260, 2200]));
c.push(P("Fruits-360 aporta variedad de variedades; las fotos propias adaptan el modelo a la luz, el fondo y la cámara reales. La clase «fondo» (sin fruta, con la mano vacía, sombras) solo puede salir del montaje y es la que permite detectar que no hay fruta. Se excluyeron variedades de Fruits-360 que se confunden entre clases (manzanas amarillas, banano rojo y una pera de color marrón similar al kiwi). [PENDIENTE: fotos propias de pera y kiwi, y recaptura con la cámara del ESP32.]"));
c.push(H2("7.4 Entrenamiento y selección del modelo"));
c.push(P("El modelo se entrenó en Edge Impulse con imágenes de 96 × 96 píxeles en color, aprendizaje por transferencia, 30 ciclos, tasa de aprendizaje 0,0005, aumento de datos y pesos por clase. Se desarrollaron seis versiones; los problemas encontrados y su solución se detallan en la sección 8.2."));
c.push(...tabla("Versiones del modelo.", ["Versión", "Cambio", "Precisión int8"], [
  ["v0", "MobileNetV2 α = 0,35", "63–72 % (float32: 100 %)"],
  ["v1", "MobileNetV1 α = 0,25", "84,3 %"],
  ["v2", "+ fotos propias de manzana verde", "similar a v1"],
  ["v3", "Corrección de etiquetas y balance de la clase manzana verde", "86,6 % (set de prueba)"],
  ["v4", "Entrenamiento con cuantización simulada (QAT)", "99,4 %"],
  ["v5", "+ 92 fotos de manzana verde en las posiciones reales de uso", "99,5 %"],
], [1100, 5460, 2800]));
c.push(P("El modelo final (v5) ocupa 300 KB. Para un ESP32 de 240 MHz, Edge Impulse estima 615 ms por inferencia, 135 KB de RAM y 297 KB de flash con la arquitectura elegida. [PENDIENTE: tiempo de inferencia medido en el ESP32-S3.]"));
c.push(H2("7.5 Firmware del ESP32-S3"));
c.push(P("El firmware captura la imagen de la OV2640 en resolución QVGA, recorta el cuadrado central y lo reduce a 96 × 96, ejecuta el modelo, aplica la lógica de confirmación y atiende las órdenes Entrada y Salida que llegan desde Home Assistant. Publica por MQTT con un `evento_id` formado por un número aleatorio de arranque y un contador. Como la librería MQTT usada publica con QoS 0, cada movimiento se guarda en una cola de hasta 8 elementos y se reenvía al reconectar; el servicio descarta los repetidos. El estado de conexión se publica con LWT y Home Assistant lo muestra como el sensor «ESP32 conectado». Soporta las placas Freenove ESP32-S3 WROOM CAM y Seeed XIAO ESP32S3 Sense. El soporte para pulsadores físicos, sensor de presencia y DHT22 ya está programado, pero desactivado por opciones de compilación (mejora futura)."));
c.push(H2("7.6 Agente conversacional"));
c.push(P("En Home Assistant se configuró un asistente que primero intenta resolver la frase con las oraciones locales y, si no encaja, la envía al agente de Ollama. El agente recibe en sus instrucciones el stock, las salidas de hoy y de la semana, el total de frutas, la fruta con menos y con más unidades, las agotadas, la que más salió en la semana y, cuando exista el sensor, la temperatura del frutero, todo calculado por plantillas de Home Assistant. Se desactivaron las herramientas de control del hogar del agente: el modelo solo consulta y no necesita actuar sobre dispositivos."));

// ---------- 8. Pruebas ----------
c.push(H1("8. Pruebas y resultados"));
c.push(H2("8.1 Pruebas automáticas"));
c.push(...tabla("Pruebas automáticas.", ["Componente", "Pruebas", "Resultado"], [
  ["Servicio (inventario, base de datos, MQTT discovery, mensajes inválidos)", "20", "20/20"],
  ["Lógica de confirmación en Python", "11", "11/11"],
  ["Lógica de confirmación en C++ (firmware)", "24 comprobaciones", "24/24"],
  ["Oraciones locales de Assist", "12", "12/12"],
], [5560, 2000, 1800]));
c.push(P("Entre ellas: confirmar solo tras 5 fotogramas seguidos; ignorar predicciones alternadas o de baja confianza; registrar **un solo** movimiento aunque se pulse varias veces con la fruta frente a la cámara durante 20 fotogramas; que un parpadeo de «fondo» no cuente como retiro; e ignorar un evento MQTT repetido."));
c.push(H2("8.2 Modelo de visión"));
c.push(H3("Problema 1: pérdida de precisión al cuantizar"));
c.push(P("El primer modelo (MobileNetV2, α = 0,35) alcanzaba 100 % en float32 pero solo 63–72 % en int8, con casi todos los errores asignados a «manzana roja» (por ejemplo, el kiwi se clasificaba como manzana roja en el 92 % de los casos). Cambiar el número de neuronas, el dropout o los ciclos de entrenamiento no lo corrigió. Para encontrar la causa se reprodujo el entrenamiento localmente con el mismo conjunto de datos y se midió el error de cuantización capa por capa (Tabla 5)."));
c.push(...tabla("Precisión según qué partes del modelo se cuantizan a int8 (reproducción local).", ["Qué se cuantiza a int8", "Precisión"], [
  ["Nada (float32)", "100 %"], ["Solo los pesos", "100 %"], ["Pesos y activaciones", "75 %"],
  ["Todo excepto la primera capa depthwise", "97 %"],
], [6560, 2800]));
c.push(P("La pérdida se concentraba en las activaciones de la primera capa *depthwise* de MobileNetV2: sus canales tienen rangos muy distintos y comparten una sola escala int8, de modo que los canales con valores pequeños, donde está la información fina de color, quedan reducidos a uno o dos niveles. Es un problema conocido de MobileNetV2 con cuantización post-entrenamiento (Nagel et al., 2019). Edge Impulse mantiene esa capa congelada, por lo que ningún ajuste de entrenamiento podía corregirla. Con MobileNetV1 (α = 0,25) la pérdida bajó a unos 8 puntos."));
c.push(H3("Problema 2: la manzana verde propia"));
c.push(P("La manzana verde de Fruits-360 se clasificaba bien, pero la del montaje solo en un 36–48 %. Al revisar las imágenes en Edge Impulse se encontraron tres manzanas verdes etiquetadas como rojas, 34 fotos tomadas fuera del montaje y una clase dominada por 150 fotos casi idénticas de una sola variedad (Granny Smith). Tras corregir las etiquetas y balancear la clase, el modelo en float32 alcanzó 98 % en esas fotos, pero en int8 se mantenía en 72 %."));
c.push(H3("Problema 3: la pérdida restante por cuantización"));
c.push(P("Se reentrenó el modelo de Edge Impulse con cuantización simulada (QAT) usando los mismos datos (Tabla 6)."));
c.push(...tabla("Cuantización post-entrenamiento frente a QAT.", ["Grupo", "Edge Impulse int8 (v3)", "QAT int8 (v4)"], [
  ["Set de prueba (172 imágenes)", "86,6 %", "99,4 %"], ["Manzana verde propia", "72 %", "100 %"],
  ["Manzana roja propia", "72 %", "98 %"], ["Manzanas confundidas con banano", "8", "0"],
], [4360, 2600, 2400]));
c.push(H3("Problema 4: errores en vivo"));
c.push(P("Con la cámara en vivo, la manzana verde se confundía con pera cuando cambiaba la posición: las fotos de entrenamiento eran ráfagas casi idénticas. Se tomaron 92 fotos en las posiciones reales de uso; en las 18 que no se usaron para entrenar, la precisión pasó de 22 % (v4) a 100 % (v5)."));
c.push(H3("Resultado final"));
c.push(P("El modelo v5 (int8) alcanza 99,5 % en el set de prueba: banano, fondo, kiwi y pera 100 %, y manzana roja 95 % (los errores van a manzana verde, que para el inventario es la misma fruta). En la prueba en vivo con la cámara del computador, el banano y las manzanas se confirmaron correctamente en el montaje."));
c.push(P("**Limitación observada.** En un ambiente distinto (otra pared, otra luz, objetos y personas al fondo) el modelo falla, como era de esperar con un modelo de 300 KB entrenado en un montaje fijo; corresponde a lo declarado fuera del alcance. En esos casos la confianza no supera el umbral y el sistema no confirma ni registra ningún movimiento."));
c.push(NOTA("Nota: el set de prueba contiene imágenes muy parecidas a las de entrenamiento (Fruits-360 fotografía cada fruta girando y las fotos propias se tomaron en ráfagas), por lo que estas cifras son optimistas. La evaluación que decide es la prueba con movimientos reales."));
c.push(figuraPendiente("matriz de confusión de v0 (MobileNetV2) y de v5"));
c.push(PEND("[PENDIENTE: resultados con la cámara del ESP32 tras reentrenar.]"));
c.push(H2("8.3 Agente conversacional"));
c.push(P("Se midió con un script que hace cada pregunta dos veces por la API de Home Assistant y compara la respuesta con el valor de los sensores en ese momento. Se distinguieron preguntas *comunes* (cubiertas por las oraciones locales) y *abiertas* (solo las puede responder el modelo de lenguaje)."));
c.push(...tabla("Resultados del agente conversacional.", ["Configuración", "Comunes", "Abiertas", "Tiempo medio"], [
  ["Oraciones locales (sin LLM)", "10/10", "0/8", "< 0,1 s"],
  ["Qwen 2.5 3B, primera versión (herramientas activadas, sin datos calculados)", "0/10", "—", "28,6 s"],
  ["Qwen 2.5 3B, versión final", "10/10", "8/8", "0,7 s"],
], [5160, 1300, 1300, 1600]));
c.push(P("En la primera versión el modelo respondía que no tenía información: las herramientas de control del hogar le entregaban la descripción de todas las entidades y el modelo intentaba usarlas en lugar de leer los datos. Al desactivarlas y entregar los totales y comparaciones ya calculados, acertó todas las preguntas. Mediciones en un computador portátil con Docker; la pregunta de temperatura se respondió con una lectura de ambiente simulada, porque el sensor quedó como mejora futura. [PENDIENTE: tiempos en la Raspberry Pi 5 y comparación con Qwen 2.5 1.5B.]"));
c.push(H2("8.4 Prueba del sistema completo"));
c.push(PEND("[PENDIENTE: 20 movimientos reales con el ESP32 y el panel de Home Assistant, mezclando frutas, entradas y salidas e incluyendo los casos difíciles (pulsar Entrada dos veces, cambiar de fruta sin retirarla, salida con stock 0). Por cada uno: fruta, tipo, si se registró correctamente y tiempo hasta confirmar. Comparar con la tabla de movimientos de SQLite.]"));

// ---------- 9. Conclusiones ----------
c.push(H1("9. Conclusiones"));
for (const t of [
  "La separación entre **identificar** (cámara y modelo) y **registrar** (orden explícita desde el panel), junto con la confirmación por fotogramas consecutivos y el estado REGISTRADA, evita que el inventario cambie con cada predicción: las pruebas muestran un único movimiento aunque la fruta permanezca visible y la orden se repita.",
  "La cuantización a int8, necesaria para el microcontrolador, puede degradar un modelo que en punto flotante es perfecto. Medir la pérdida capa por capa permitió identificar la causa en lugar de probar ajustes al azar, y el entrenamiento con cuantización simulada eliminó la diferencia entre float32 e int8.",
  "La calidad de los datos pesó más que la arquitectura en las clases difíciles: etiquetas incorrectas, fotos fuera del montaje y una clase dominada por una sola variedad explicaban los errores de la manzana verde.",
  "Combinar oraciones locales con un modelo de lenguaje pequeño da respuestas exactas e inmediatas para las preguntas frecuentes y deja al modelo solo las abiertas. Entregarle los datos ya calculados fue decisivo para que un modelo de 3B respondiera correctamente.",
  "Desarrollar con simuladores que respetan el mismo protocolo MQTT permitió completar y probar el software antes de disponer del hardware.",
  "[PENDIENTE: conclusión sobre el desempeño con movimientos reales y los tiempos en la Raspberry Pi.]",
]) c.push(VIN(t));
c.push(H2("9.1 Trabajo futuro"));
for (const t of [
  "Estación física de registro: caja con fondo e iluminación fijos, pulsadores Entrada y Salida, LED y sensor de presencia, para registrar sin el celular. El firmware ya la soporta (opciones de compilación) y su plano y conexiones están documentados en el repositorio.",
  "Sensor de temperatura y humedad (DHT22) para las condiciones de conservación: Home Assistant y el agente ya tienen los sensores preparados.",
  "Fotos propias de pera y kiwi, y recaptura del conjunto de datos con la cámara del ESP32.",
  "Robustez a otros ambientes: fotos en varios lugares y una clase «fondo» más variada.",
  "Detección de objetos (por ejemplo FOMO) para reconocer varias frutas a la vez.",
  "Pronóstico de consumo cuando se acumulen varias semanas de historial.",
]) c.push(VIN(t));

// ---------- Referencias ----------
c.push(H1("Referencias"));
for (const t of [
  "Howard, A. G., Zhu, M., Chen, B., Kalenichenko, D., Wang, W., Weyand, T., Andreetto, M. y Adam, H. (2017). *MobileNets: Efficient convolutional neural networks for mobile vision applications*. arXiv:1704.04861.",
  "Hymel, S., Banbury, C., Situnayake, D., Elium, A., Ward, C., Kelcey, M., Baaijens, M., Majchrzycki, M., Plunkett, J., Tischler, D., Grande, A., Moreau, L., Maslov, D., Beavis, A., Jongboom, J. y Reddi, V. J. (2022). *Edge Impulse: An MLOps platform for tiny machine learning*. arXiv:2212.03332.",
  "Jacob, B., Kligys, S., Chen, B., Zhu, M., Tang, M., Howard, A., Adam, H. y Kalenichenko, D. (2018). Quantization and training of neural networks for efficient integer-arithmetic-only inference. En *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*.",
  "Krishnamoorthi, R. (2018). *Quantizing deep convolutional networks for efficient inference: A whitepaper*. arXiv:1806.08342.",
  "Mureșan, H. y Oltean, M. (2018). Fruit recognition from images using deep learning. *Acta Universitatis Sapientiae, Informatica, 10*(1), 26–42.",
  "Nagel, M., van Baalen, M., Blankevoort, T. y Welling, M. (2019). Data-free quantization through weight equalization and bias correction. En *Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)*.",
  "OASIS. (2014). *MQTT Version 3.1.1*. OASIS Standard.",
  "Qwen Team. (2024). *Qwen2.5 technical report*. arXiv:2412.15115.",
  "Sandler, M., Howard, A., Zhu, M., Zhmoginov, A. y Chen, L.-C. (2018). MobileNetV2: Inverted residuals and linear bottlenecks. En *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*.",
  "Warden, P. y Situnayake, D. (2019). *TinyML: Machine learning with TensorFlow Lite on Arduino and ultra-low-power microcontrollers*. O'Reilly Media.",
  "Home Assistant. (s. f.). *Documentación de Home Assistant*. https://www.home-assistant.io/docs/",
]) c.push(REF(t));

// =====================================================================
const encabezado = (tam, antes, despues) => ({ run: { font: FUENTE, size: tam, bold: true, color: "000000" },
  paragraph: { spacing: { before: antes, after: despues }, keepNext: true } });
const doc = new Document({
  creator: "", title: "FruitAI", description: "Documento del proyecto FruitAI",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FUENTE, size: 24 } }, title: { run: { font: FUENTE, size: 56, bold: true } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        ...encabezado(30, 360, 160), paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        ...encabezado(26, 240, 120), paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FUENTE, size: 24, bold: true, italics: true, color: "000000" },
        paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "vinetas", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ...["objetivos", "flujo", "estados"].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL,
      text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] })),
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
    children: c,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[2] || "FruitAI_documento.docx", b); console.log("ok"); });
