import streamlit as st
from google import genai
import requests
from streamlit_lottie import st_lottie
import time
import re
from datetime import datetime

# ============================================================
#  🎬 LINK DEL VIDEO TUTORIAL
#  Pega aquí el enlace de tu video (YouTube, Drive, etc.)
#  Ejemplo: "https://www.youtube.com/watch?v=abc123"
#  Mientras esté vacío, el botón avisará que aún no hay video.
# ============================================================
LINK_TUTORIAL = ""

# --- LIMPIEZA DE TEXTO PARA LA VOZ ---
# Quita muletillas ('mmm', 'hmm', 'ajá'...), acotaciones entre asteriscos y emojis
# para que la voz nunca pronuncie "eme eme eme" ni lea símbolos.
def limpiar_para_voz(texto):
    if not texto:
        return texto
    # Quitar acotaciones entre asteriscos: *piensa*, *sonríe*
    texto = re.sub(r'\*[^*]*\*', '', texto)
    # Quitar muletillas y sonidos de duda (palabras sueltas tipo mmm, hmm, ehh, ajá)
    texto = re.sub(r'\b(m{2,}|h?m{2,}|hmm+|ajá+|aja+|eh+|este\.{2,}|uhm+|umm+)\b',
                   '', texto, flags=re.IGNORECASE)
    # Quitar emojis y símbolos pictográficos
    texto = re.sub(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]', '', texto)
    # Quitar markdown sobrante (#, *, _)
    texto = re.sub(r'[#*_`]', '', texto)
    # Limpiar espacios dobles y signos de puntuación huérfanos
    texto = re.sub(r'\s{2,}', ' ', texto)
    texto = re.sub(r'\s+([.,;:!?])', r'\1', texto)
    # Colapsar signos repetidos que quedaron al borrar muletillas (",,"  ".,"  "..,")
    texto = re.sub(r'([.,;:!?])[\s.,;:]+', r'\1 ', texto)
    # Quitar puntuación y espacios sobrantes al inicio de cada frase
    texto = re.sub(r'^[\s.,;:!?]+', '', texto)
    texto = re.sub(r'(?<=[.!?])\s+[,;:]+', ' ', texto)
    texto = re.sub(r'\s{2,}', ' ', texto)
    return texto.strip()

# --- 1. CONFIGURACIÓN DE ATHENA ---
st.set_page_config(page_title="Athena AI", layout="centered")

# 🔑 API KEY DE GEMINI
# La clave se lee desde st.secrets (segura, NO va escrita en el código).
# - En tu PC: ponla en .streamlit/secrets.toml
# - En Streamlit Cloud: ponla en Settings -> Secrets
try:
    GEMINI_API_KEY = st.secrets["gemini_api_key"]
except Exception:
    st.error("Falta configurar la clave de Gemini. Agrega 'gemini_api_key' en los Secrets.")
    st.stop()
client = genai.Client(api_key=GEMINI_API_KEY)

# --- FUNCIÓN PARA GENERAR RESPUESTAS (con reintento ante límite de cuota) ---
def generar_respuesta(contenido):
    for intento in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',  # modelo liviano = más cuota gratis
                contents=contenido
            )
            return limpiar_para_voz(response.text)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "RESOURCEEXHAUSTED" in err:
                if intento < 2:
                    time.sleep(5)
                    continue
                return ("Disculpa, en este momento alcancé el límite de uso del servicio. "
                        "Por favor intenta de nuevo en unos minutos.")
            else:
                return ("Disculpa, tuve un problema técnico para responderte. "
                        "Intentemos de nuevo.")

# --- GUARDADO LOCAL DE SESIONES (dentro de la app, en un archivo) ---
import json
import os

ARCHIVO_REGISTROS = "registros_athena.json"

def cargar_registros():
    """Lee todas las sesiones guardadas del archivo."""
    try:
        if os.path.exists(ARCHIVO_REGISTROS):
            with open(ARCHIVO_REGISTROS, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def guardar_registro(nombre, correo, grado, modo, mensajes):
    """Añade una sesión nueva al archivo (permanente, no se borra)."""
    try:
        registros = cargar_registros()
        registros.append({
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "nombre": nombre,
            "correo": correo,
            "grado": grado,
            "modo": modo,
            "mensajes": mensajes,
        })
        with open(ARCHIVO_REGISTROS, "w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# --- 2. MEMORIA Y ESTADOS ---
if 'paso' not in st.session_state: st.session_state.paso = "registro"
if 'mensajes' not in st.session_state: st.session_state.mensajes = []

# --- 3. DISEÑO Y ESTILO ---
st.markdown("""
    <style>
    /* ===== ANIMACIONES ===== */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(25px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes glowTitle {
        0%, 100% { text-shadow: 0 4px 30px rgba(96,165,250,0.25); }
        50%      { text-shadow: 0 4px 45px rgba(96,165,250,0.6), 0 0 20px rgba(59,130,246,0.4); }
    }
    @keyframes floatBg {
        0%   { background-position: 0px 0px, 0px 0px; }
        100% { background-position: 400px 600px, -300px 500px; }
    }
    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    @keyframes popIn {
        0%   { opacity: 0; transform: scale(0.92) translateY(15px); }
        60%  { opacity: 1; transform: scale(1.02); }
        100% { opacity: 1; transform: scale(1) translateY(0); }
    }

    /* ===== FONDO GENERAL ===== */
    .stApp {
        background:
            radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.35), transparent),
            radial-gradient(2px 2px at 70% 60%, rgba(255,255,255,0.25), transparent),
            radial-gradient(1.5px 1.5px at 40% 80%, rgba(148,197,255,0.4), transparent),
            radial-gradient(1.5px 1.5px at 90% 20%, rgba(255,255,255,0.2), transparent),
            radial-gradient(1200px 600px at 50% -10%, #1f2937 0%, #0b1120 55%, #070b14 100%);
        background-size: 600px 600px, 500px 500px, 450px 450px, 400px 400px, 100% 100%;
        animation: floatBg 60s linear infinite;
    }
    .block-container {
        padding-top: 2.5rem;
        animation: fadeIn 0.8s ease;
    }

    /* ===== HEADER ===== */
    .header-container {
        background: linear-gradient(135deg, #1e293b 0%, #111827 60%, #0f172a 100%);
        padding: 45px 10px;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 38px;
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        box-shadow: 0 20px 50px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.05);
        border: 1px solid rgba(148,163,184,0.15);
        animation: fadeInUp 0.9s ease;
    }
    .athena-title {
        font-family: 'Georgia', 'serif';
        background: linear-gradient(90deg, #ffffff 0%, #93c5fd 25%, #ffffff 50%, #93c5fd 75%, #ffffff 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: clamp(90px, 18vw, 230px);
        font-weight: 900;
        letter-spacing: 18px;
        margin: 0;
        line-height: 1;
        text-transform: uppercase;
        white-space: nowrap;
        animation: shimmer 6s linear infinite;
        filter: drop-shadow(0 4px 30px rgba(96,165,250,0.3));
    }
    .titulo-sistem {
        font-size: clamp(40px, 9vw, 110px) !important;
        letter-spacing: 10px !important;
    }
    .header-sub {
        color: #94a3b8;
        font-family: sans-serif;
        font-size: 15px;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin-top: -6px;
        animation: fadeInUp 1.2s ease both;
        animation-delay: 0.3s;
    }

    /* ===== TEXTOS ===== */
    h1, h2, h3, h4, p, label, .stMarkdown {
        color: #e2e8f0 !important;
    }

    /* ===== INPUTS ===== */
    .stTextInput>div>div>input,
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59,130,246,0.3) !important;
    }
    /* El input del DNI pegado al dominio (sin borde derecho ni esquinas) */
    .stTextInput>div>div>input {
        border-radius: 12px 0px 0px 12px !important;
        border-right: none !important;
    }
    .email-union {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-left: none;
        padding: 0px 12px;
        border-radius: 0px 12px 12px 0px;
        height: 40px;
        display: flex;
        align-items: center;
        color: #94a3b8;
        font-family: monospace;
        font-size: 13px;
        white-space: nowrap;
        overflow: hidden;
    }
    /* Pegamos las columnas para que el DNI y el dominio se vean como un solo cuadro */
    div[data-testid="stHorizontalBlock"] {
        gap: 0rem !important;
    }

    /* ===== TARJETAS DEL MENÚ ===== */
    div[data-testid="stAlert"] {
        margin: 0 8px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(148,163,184,0.2) !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        backdrop-filter: blur(4px);
        animation: popIn 0.7s ease both;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    div[data-testid="stAlert"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 40px rgba(0,0,0,0.45) !important;
    }

    /* ===== BOTONES ===== */
    .stButton>button {
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        color: #fff !important;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        padding: 10px 22px !important;
        box-shadow: 0 8px 20px rgba(37,99,235,0.35) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 26px rgba(37,99,235,0.5) !important;
        background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%) !important;
    }
    .stButton>button:active {
        transform: translateY(0) !important;
    }
    /* Botón de descarga con el mismo estilo */
    .stDownloadButton>button {
        border-radius: 14px !important;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #fff !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 20px rgba(5,150,105,0.35) !important;
    }

    /* ===== CHAT (transcripción) ===== */
    div[data-testid="stChatMessage"] {
        background: rgba(30,41,59,0.6) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(148,163,184,0.12) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# CRÉDITOS FLOTANTES (efecto cristal) — SOLO en la pantalla de inicio (registro)
if st.session_state.paso == "registro":
    st.markdown("""
    <style>
    @keyframes flota1 {
        0%   { transform: translate(0, 0) rotate(-4deg); }
        50%  { transform: translate(20px, -30px) rotate(3deg); }
        100% { transform: translate(0, 0) rotate(-4deg); }
    }
    @keyframes flota2 {
        0%   { transform: translate(0, 0) rotate(5deg); }
        50%  { transform: translate(-25px, 25px) rotate(-3deg); }
        100% { transform: translate(0, 0) rotate(5deg); }
    }
    @keyframes flota3 {
        0%   { transform: translate(0, 0) rotate(2deg); }
        50%  { transform: translate(18px, 28px) rotate(-5deg); }
        100% { transform: translate(0, 0) rotate(2deg); }
    }
    @keyframes flota4 {
        0%   { transform: translate(0, 0) rotate(-3deg); }
        50%  { transform: translate(-20px, -22px) rotate(4deg); }
        100% { transform: translate(0, 0) rotate(-3deg); }
    }
    .creditos-capa {
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    .credito {
        position: absolute;
        font-family: 'Georgia', serif;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: rgba(255,255,255,0.55);
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 16px;
        padding: 10px 22px;
        backdrop-filter: blur(6px);
        -webkit-backdrop-filter: blur(6px);
        box-shadow: 0 8px 32px rgba(31,38,135,0.25), inset 0 1px 0 rgba(255,255,255,0.2);
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        white-space: nowrap;
    }
    /* Posiciones en pantalla normal (PC) */
    .c1 { top: 12%; left: 6%;  font-size: 22px; animation: flota1 14s ease-in-out infinite; }
    .c2 { top: 22%; right: 6%; font-size: 24px; animation: flota2 18s ease-in-out infinite; }
    .c3 { bottom: 24%; left: 8%; font-size: 22px; animation: flota3 16s ease-in-out infinite; }
    .c4 { bottom: 10%; right: 7%; font-size: 20px; animation: flota4 20s ease-in-out infinite; }

    /* En celular: nombres más chicos y bien separados en las 4 esquinas */
    @media (max-width: 640px) {
        .credito {
            font-size: 15px !important;
            padding: 6px 12px;
            letter-spacing: 2px;
        }
        .c1 { top: 8%;  left: 5%;  right: auto; }
        .c2 { top: 8%;  right: 5%; left: auto; }
        .c3 { bottom: 8%; left: 5%; right: auto; top: auto; }
        .c4 { bottom: 8%; right: 5%; left: auto; top: auto; }
    }
    /* Aseguramos que el contenido real quede por encima de los créditos */
    .block-container { position: relative; z-index: 1; }
    </style>
    <div class="creditos-capa">
        <div class="credito c1">Valery</div>
        <div class="credito c2">Daniela</div>
        <div class="credito c3">Alberto</div>
        <div class="credito c4">Emmanuel</div>
    </div>
    """, unsafe_allow_html=True)

    # --- ESTILO DEL BOTÓN "TUTORIAL" (mismo cristal que los créditos) ---
    st.markdown("""
    <style>
    @keyframes flotaTutorial {
        0%, 100% { transform: translateY(0); }
        50%      { transform: translateY(-8px); }
    }
    /* El botón Tutorial usa el estilo cristal, no el azul del resto */
    div[data-testid="stButton"] button[kind="secondary"] {
        font-family: 'Georgia', serif !important;
        font-weight: 700 !important;
        letter-spacing: 3px !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.8) !important;
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.22) !important;
        border-radius: 16px !important;
        padding: 10px 24px !important;
        backdrop-filter: blur(6px) !important;
        -webkit-backdrop-filter: blur(6px) !important;
        box-shadow: 0 8px 32px rgba(31,38,135,0.25), inset 0 1px 0 rgba(255,255,255,0.2) !important;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
        animation: flotaTutorial 3.5s ease-in-out infinite;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.14) !important;
        border-color: rgba(255,255,255,0.4) !important;
        transform: translateY(-3px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# CABECERA PRINCIPAL — oculta en la pantalla de despedida
if st.session_state.paso != "despedida":
    if st.session_state.paso == "panel_admin":
        titulo_header = "ATHENA SISTEM"
        subtitulo_header = ""
        clase_titulo = "athena-title titulo-sistem"
    else:
        titulo_header = "ATHENA"
        subtitulo_header = "Tu asistente de reflexión y bienestar"
        clase_titulo = "athena-title"
    st.markdown(f"""
    <div class="header-container">
        <p class="{clase_titulo}">{titulo_header}</p>
    </div>
    <p class="header-sub" style="text-align:center;">{subtitulo_header}</p>
    """, unsafe_allow_html=True)

# --- 4. LÓGICA DE PANTALLAS ---

# PANTALLA: REGISTRO
if st.session_state.paso == "registro":
    nombre = st.text_input("Nombre Completo:")

    st.markdown("DNI / Usuario:")
    col_dni, col_dom = st.columns([2, 1.6])
    with col_dni:
        dni = st.text_input("DNI / Usuario:", label_visibility="collapsed", placeholder="Tu DNI")
    with col_dom:
        st.markdown('<div class="email-union">@alumnos.innovaschools.edu.pe</div>', unsafe_allow_html=True)

    grado = st.selectbox("Grado:", ["1ero Secundaria", "2do Secundaria", "3ero Secundaria", "4to Secundaria", "5to Secundaria"])

    st.write(" ")
    if st.button("ACCEDER"):
        # CLAVE SECRETA DEL PROFESOR: escribir "system regist" en el nombre
        if nombre.strip().lower() == "system regist":
            st.session_state.paso = "panel_admin"
            st.rerun()
        elif nombre and dni:
            st.session_state.usuario = nombre
            st.session_state.dni = dni
            st.session_state.correo = f"{dni}@alumnos.innovaschools.edu.pe"
            st.session_state.grado = grado
            st.session_state.paso = "menu"
            st.balloons()
            st.rerun()
        else:
            st.toast("Por favor, completa todos los campos para ingresar.")

    # --- BOTÓN TUTORIAL (estilo cristal, abre el video dentro de la app) ---
    st.write(" ")
    if 'ver_tutorial' not in st.session_state:
        st.session_state.ver_tutorial = False

    col_izq, col_tut, col_der = st.columns([1, 1.2, 1])
    with col_tut:
        etiqueta = "✕ Cerrar tutorial" if st.session_state.ver_tutorial else "🎬 Tutorial"
        if st.button(etiqueta, type="secondary"):
            st.session_state.ver_tutorial = not st.session_state.ver_tutorial
            st.rerun()

    # Mostramos el video dentro de la app
    if st.session_state.ver_tutorial:
        if LINK_TUTORIAL.strip():
            st.video(LINK_TUTORIAL)
        else:
            st.info("El video del tutorial aún no está configurado. "
                    "Pega el enlace en la variable LINK_TUTORIAL, al inicio del código.")

# PANTALLA: MENÚ (REFLEXIÓN O CONSEJERO)
elif st.session_state.paso == "menu":
    st.markdown(f"""
        <div style="text-align:center; margin-bottom:20px;">
            <h2 style="margin-bottom:4px;">Bienvenido, {st.session_state.usuario} 👋</h2>
            <p style="color:#94a3b8;">Selecciona tu ruta de trabajo para hoy</p>
        </div>
    """, unsafe_allow_html=True)

    col_ref, col_cons = st.columns(2)

    with col_ref:
        st.info("### Reflexión\n(Sobre tu conducta)\nUn espacio para pensar sobre lo ocurrido.")
        if st.button("Iniciar Reflexión"):
            st.session_state.modo = "Reflexión de conducta"
            st.session_state.instruccion = (
                "Eres Athena, una tutora de Innova Schools que acompaña a un alumno a reflexionar sobre una falta o mala conducta que cometió. "
                "Tu objetivo es que el alumno reconozca lo que hizo, comprenda por qué estuvo mal, identifique a quién afectó y piense cómo repararlo y evitar repetirlo. "
                "Mantén un tono firme pero respetuoso, calmado y constructivo, nunca humillante ni agresivo. No regañes ni juzgues: guía con preguntas. "
                "Haz UNA pregunta a la vez y deja que el alumno se exprese. Ayúdalo a llegar a sus propias conclusiones en lugar de darle sermones. "
                "Reconoce cuando muestre honestidad o ganas de mejorar. "
                "Responde de forma breve y conversacional, como en una llamada de voz. "
                "IMPORTANTE: No escribas muletillas ni sonidos de duda como 'mmm', 'hmm', 'ajá', 'eh', 'este...'. "
                "No uses acotaciones entre asteriscos como *piensa* ni emojis. Escribe solo palabras reales y completas, listas para ser leídas en voz alta."
            )
            st.session_state.paso = "chat"
            st.session_state.reset_timer = True
            st.rerun()

    with col_cons:
        st.success("### Consejero\n(Ruta Personal)\nConversación libre de apoyo. No afecta tus notas.")
        if st.button("Hablar con Consejero"):
            st.session_state.modo = "Personal"
            st.session_state.instruccion = "Eres Athena, una consejera amable y empática. Escucha al alumno y dale consejos de bienestar. Tono cercano. Responde de forma breve y conversacional, como en una llamada de voz. IMPORTANTE: No escribas muletillas ni sonidos de duda como 'mmm', 'hmm', 'ajá', 'eh', 'este...'. No uses acotaciones entre asteriscos como *piensa* ni emojis. Escribe solo palabras reales y completas, listas para ser leídas en voz alta."
            st.session_state.paso = "chat"
            st.session_state.reset_timer = True
            st.rerun()

# PANTALLA: CHAT CON IA (MODO LLAMADA)
elif st.session_state.paso == "chat":

    if 'mensajes' not in st.session_state: st.session_state.mensajes = []
    if 'ultima_respuesta_ia' not in st.session_state: st.session_state.ultima_respuesta_ia = ""

    # --- ATHENA TOMA LA INICIATIVA ---
    # Si la conversación está vacía, Athena saluda y hace la primera pregunta.
    if len(st.session_state.mensajes) == 0:
        with st.spinner("Athena se está conectando..."):
            nombre_alumno = st.session_state.get("usuario", "").split(" ")[0]
            if st.session_state.get("modo") == "Reflexión de conducta":
                indicacion_apertura = (
                    f"Saluda al alumno por su nombre ({nombre_alumno}) de forma serena y respetuosa, "
                    f"explícale en una frase que este es un espacio para reflexionar juntos sobre lo que sucedió, "
                    f"y pregúntale con calma qué fue lo que pasó. "
                    f"No lo regañes ni asumas detalles que no conoces."
                )
            else:
                indicacion_apertura = (
                    f"Saluda al alumno por su nombre ({nombre_alumno}) de forma cálida y breve, "
                    f"y hazle UNA sola pregunta abierta sobre cómo se siente para iniciar la conversación."
                )
            apertura = (
                f"{st.session_state.instruccion}\n\n"
                f"Esta es la primera vez que hablas en esta llamada. "
                f"{indicacion_apertura} "
                f"No esperes a que el alumno hable primero, toma tú la iniciativa. "
                f"Responde como Athena en 1 o 2 frases."
            )
            saludo = generar_respuesta(apertura)
        st.session_state.mensajes.append({"role": "assistant", "content": saludo})
        st.session_state.ultima_respuesta_ia = saludo
        st.rerun()

    # El chat_input sigue existiendo (lo usa el micrófono para inyectar el texto),
    # pero lo ocultamos visualmente: en esta pantalla SOLO se ve la burbuja.
    st.markdown("""
        <style>
        [data-testid="stChatInput"] { opacity: 0; height: 0; overflow: hidden; }
        </style>
    """, unsafe_allow_html=True)

    prompt = st.chat_input("Escribe tu mensaje o habla directamente...")

    if prompt:
        # Se guarda en segundo plano, NO se muestra en pantalla
        st.session_state.mensajes.append({"role": "user", "content": prompt})

        # Construimos el contexto con el historial para una conversación continua
        historial = "\n".join(
            [f"{'Alumno' if m['role']=='user' else 'Athena'}: {m['content']}" for m in st.session_state.mensajes]
        )
        contenido = f"{st.session_state.instruccion}\n\nConversación hasta ahora:\n{historial}\n\nResponde como Athena:"

        respuesta_texto = generar_respuesta(contenido)
        # Se guarda en segundo plano, NO se muestra en pantalla
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta_texto})
        st.session_state.ultima_respuesta_ia = respuesta_texto
        st.rerun()

    # --- MOTOR DE VOZ Y MICRÓFONO AUTOMÁTICO (MODO LLAMADA) ---
    texto_a_hablar = (
        st.session_state.ultima_respuesta_ia
        .replace('"', '\\"')
        .replace('\n', ' ')
        .replace("'", "\\'")
        if st.session_state.ultima_respuesta_ia else ""
    )

    # Si venimos de iniciar una llamada nueva, reiniciamos el timer (solo una vez)
    reset_timer_js = "true" if st.session_state.get("reset_timer") else "false"
    st.session_state.reset_timer = False

    script_gemini_live = f"""
    <style>
        @keyframes onda {{
            0%, 100% {{ transform: scaleY(0.3); }}
            50% {{ transform: scaleY(1); }}
        }}
        @keyframes pulso {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(59,130,246,0.5); }}
            50% {{ box-shadow: 0 0 0 22px rgba(59,130,246,0); }}
        }}
        @keyframes pulsoVerde {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(52,211,153,0.45); }}
            50% {{ box-shadow: 0 0 0 18px rgba(52,211,153,0); }}
        }}
        @keyframes respirar {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.06); }}
        }}
        @keyframes aparecer {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        .call-box {{ animation: aparecer 0.7s ease both; }}
        .burbuja {{
            width: 100px; height: 100px;
            margin: 0 auto 18px auto;
            border-radius: 50%;
            background: #1f2937;
            display: flex; align-items: center; justify-content: center;
            gap: 5px;
            transition: all 0.3s ease;
            animation: respirar 3s ease-in-out infinite;
        }}
        .burbuja.hablando {{
            background: #1e3a8a;
            animation: pulso 1.5s infinite, respirar 2s ease-in-out infinite;
        }}
        .barra {{
            width: 6px; height: 42px;
            background: #4b5563;
            border-radius: 3px;
            transform: scaleY(0.3);
        }}
        .burbuja.hablando .barra {{
            background: #60a5fa;
            animation: onda 0.9s infinite ease-in-out;
        }}
        .burbuja.hablando .barra:nth-child(2) {{ animation-delay: 0.15s; }}
        .burbuja.hablando .barra:nth-child(3) {{ animation-delay: 0.3s; }}
        .burbuja.hablando .barra:nth-child(4) {{ animation-delay: 0.45s; }}
        .burbuja.escuchando {{
            background: #064e3b;
            animation: pulsoVerde 2s infinite, respirar 3s ease-in-out infinite;
        }}
        .burbuja.escuchando .barra {{
            background: #34d399;
            animation: onda 1.4s infinite ease-in-out;
        }}
        .burbuja.escuchando .barra:nth-child(2) {{ animation-delay: 0.2s; }}
        .burbuja.escuchando .barra:nth-child(3) {{ animation-delay: 0.4s; }}
        .burbuja.escuchando .barra:nth-child(4) {{ animation-delay: 0.6s; }}
    </style>
    <div class="call-box" style="position: relative; background: linear-gradient(135deg, #1e293b 0%, #111827 70%); color: #ffffff; padding: 28px 20px; border-radius: 20px; text-align: center; font-family: sans-serif; box-shadow: 0 18px 45px rgba(0,0,0,0.45); border: 1px solid rgba(148,163,184,0.18);">
        <div id="timer" style="position: absolute; top: 12px; right: 16px; background: #1f2937; color: #f3f4f6; font-size: 20px; font-weight: bold; font-family: monospace; padding: 6px 14px; border-radius: 10px; border: 1px solid #374151;">05:00</div>
        <div id="burbuja" class="burbuja escuchando">
            <div class="barra"></div>
            <div class="barra"></div>
            <div class="barra"></div>
            <div class="barra"></div>
        </div>
        <div id="status-mode" style="font-size: 20px; font-weight: bold; color: #10b981; margin-bottom: 6px;">🟢 En llamada</div>
        <p id="status-desc" style="color: #9ca3af; margin: 0;">Conectando con Athena...</p>
        <button id="btn-escuchar" style="margin-top:15px; background:#3b82f6; color:#fff; border:none; padding:10px 20px; border-radius:10px; cursor:pointer; display:none;">
            🔊 Escuchar otra vez
        </button>
    </div>

    <script>
    var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'es-PE';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    var vocesListas = false;
    var vozFemenina = null;

    // Precarga de voces: clave para que SIEMPRE suene femenina
    function cargarVoces() {{
        var voices = window.speechSynthesis.getVoices();
        if (!voices.length) return;

        // Prioridad: nombres de voces femeninas conocidas en español
        var preferidas = ['monica', 'helena', 'paulina', 'zira', 'sabina', 'laura', 'female', 'mujer'];
        for (var p of preferidas) {{
            vozFemenina = voices.find(v => v.lang.includes('es') && v.name.toLowerCase().includes(p));
            if (vozFemenina) break;
        }}
        // Google español suele ser femenina
        if (!vozFemenina) vozFemenina = voices.find(v => v.lang.includes('es') && v.name.toLowerCase().includes('google'));
        // Última opción: cualquier voz en español
        if (!vozFemenina) vozFemenina = voices.find(v => v.lang.includes('es'));

        vocesListas = true;
    }}

    cargarVoces();
    window.speechSynthesis.onvoiceschanged = cargarVoces;

    function activarMicrofono() {{
        try {{
            document.getElementById("burbuja").className = "burbuja escuchando";
            document.getElementById("status-mode").innerText = "🟢 Escuchando";
            document.getElementById("status-mode").style.color = "#10b981";
            document.getElementById("status-desc").innerText = "Habla, te escucho...";
            recognition.start();
        }} catch(e) {{ }}
    }}

    recognition.onresult = function(event) {{
        var textoResult = event.results[0][0].transcript;
        document.getElementById("burbuja").className = "burbuja";
        document.getElementById("status-desc").innerText = "Enviando a Athena...";

        const v = parent.document.querySelector('textarea[aria-label="Escribe tu mensaje o habla directamente..."]');
        if (v) {{
            const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            setter.call(v, textoResult);
            v.dispatchEvent(new Event('input', {{ bubbles: true }}));
            setTimeout(() => {{
                const contenedorInput = v.closest('[data-testid="stChatInput"]');
                const botonEnviar = contenedorInput ? contenedorInput.querySelector('button') : null;
                if (botonEnviar) {{
                    botonEnviar.click();
                }} else {{
                    v.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', keyCode: 13, bubbles: true }}));
                }}
            }}, 200);
        }}
    }};

    recognition.onerror = function() {{ setTimeout(activarMicrofono, 800); }};

    // Si no hay nada que decir, vuelve a escuchar automáticamente
    recognition.onend = function() {{
        if ("{texto_a_hablar}" === "") {{
            setTimeout(activarMicrofono, 300);
        }}
    }};

    function hablarAthena() {{
        document.getElementById("burbuja").className = "burbuja hablando";
        document.getElementById("status-mode").innerText = "🔊 Athena habla";
        document.getElementById("status-mode").style.color = "#3b82f6";
        document.getElementById("status-desc").innerText = "Escucha...";

        window.speechSynthesis.cancel();
        if (!vocesListas) cargarVoces();

        var msg = new SpeechSynthesisUtterance("{texto_a_hablar}");
        msg.lang = 'es-ES';
        msg.rate = 1.05;
        msg.pitch = 1.15;   // tono un poco más alto = más femenino
        msg.volume = 1.0;
        if (vozFemenina) msg.voice = vozFemenina;

        // Al terminar de hablar -> reabrir micrófono (mantiene la "llamada")
        msg.onend = function() {{
            setTimeout(activarMicrofono, 250);
        }};

        window.speechSynthesis.speak(msg);
    }}

    document.getElementById('btn-escuchar').onclick = hablarAthena;

    if ("{texto_a_hablar}" !== "") {{
        document.getElementById('btn-escuchar').style.display = 'inline-block';
        // Pequeño retraso para asegurar que las voces estén cargadas
        setTimeout(hablarAthena, 350);
    }} else {{
        setTimeout(activarMicrofono, 400);
    }}

    // --- TIMER DE 5 MINUTOS (continuo aunque el componente se recargue) ---
    var DURACION = 5 * 60 * 1000; // 5 minutos en ms
    // Si es una llamada nueva, reiniciamos el conteo
    if ({reset_timer_js}) {{ sessionStorage.removeItem('athena_inicio'); }}
    var inicio = sessionStorage.getItem('athena_inicio');
    if (!inicio) {{
        inicio = Date.now().toString();
        sessionStorage.setItem('athena_inicio', inicio);
    }}
    inicio = parseInt(inicio);

    var sesionTerminada = false;

    function terminarPorTiempo() {{
        if (sesionTerminada) return;
        sesionTerminada = true;
        try {{ recognition.abort(); }} catch(e) {{}}
        try {{ window.speechSynthesis.cancel(); }} catch(e) {{}}
        document.getElementById("status-mode").innerText = "⏱️ Tiempo cumplido";
        document.getElementById("status-mode").style.color = "#ef4444";
        document.getElementById("status-desc").innerText = "La sesión ha terminado.";
        document.getElementById("burbuja").className = "burbuja";
        sessionStorage.removeItem('athena_inicio');
        // Pulsamos el botón "Terminar Sesión" de Streamlit para pasar a la transcripción
        const botones = parent.document.querySelectorAll('button');
        for (const b of botones) {{
            if (b.innerText.trim() === "Terminar Sesión") {{ b.click(); break; }}
        }}
    }}

    function actualizarTimer() {{
        var restante = DURACION - (Date.now() - inicio);
        if (restante <= 0) {{
            document.getElementById("timer").innerText = "00:00";
            document.getElementById("timer").style.color = "#ef4444";
            terminarPorTiempo();
            return;
        }}
        var min = Math.floor(restante / 60000);
        var seg = Math.floor((restante % 60000) / 1000);
        var txt = (min < 10 ? "0" : "") + min + ":" + (seg < 10 ? "0" : "") + seg;
        var el = document.getElementById("timer");
        el.innerText = txt;
        // Último minuto en rojo como aviso
        el.style.color = (restante <= 60000) ? "#ef4444" : "#f3f4f6";
        el.style.borderColor = (restante <= 60000) ? "#ef4444" : "#374151";
    }}

    actualizarTimer();
    setInterval(actualizarTimer, 500);
    </script>
    """
    st.components.v1.html(script_gemini_live, height=325)

    st.write(" ")
    if st.button("Terminar Sesión"):
        # Guardamos la sesión en el archivo de la app (permanente, no se borra)
        if st.session_state.mensajes:
            guardar_registro(
                st.session_state.get("usuario", "-"),
                st.session_state.get("correo", "-"),
                st.session_state.get("grado", "-"),
                st.session_state.get("modo", "-"),
                list(st.session_state.mensajes),
            )
        st.session_state.ultima_respuesta_ia = ""
        st.session_state.paso = "despedida"
        st.rerun()

# PANTALLA: DESPEDIDA
elif st.session_state.paso == "despedida":
    st.markdown("""
        <style>
        @keyframes flotaDespedida {
            0%, 100% { transform: translateY(0); }
            50%      { transform: translateY(-18px); }
        }
        /* Ocultamos por completo cualquier resto de interfaz en la despedida */
        [data-testid="stChatInput"], [data-testid="stToolbar"] { display: none !important; }
        </style>
        <div style="text-align:center; margin-top:120px; animation: fadeInUp 1s ease;">
            <div style="
                font-family: 'Georgia', serif;
                font-size: clamp(50px, 12vw, 110px);
                font-weight: 900;
                background: linear-gradient(90deg, #ffffff 0%, #93c5fd 50%, #ffffff 100%);
                background-size: 200% auto;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                animation: shimmer 6s linear infinite, flotaDespedida 4s ease-in-out infinite;
                margin-bottom: 6px;
                filter: drop-shadow(0 6px 30px rgba(96,165,250,0.35));
            ">Gracias</div>
            <p style="
                color:#cbd5e1; font-size:28px; letter-spacing:4px; margin:0;
                animation: flotaDespedida 4s ease-in-out infinite; animation-delay: 0.4s;
            ">Hasta luego...</p>
        </div>
    """, unsafe_allow_html=True)

    # Espera 10 segundos y vuelve al punto de registro
    time.sleep(10)
    st.session_state.mensajes = []
    st.session_state.ultima_respuesta_ia = ""
    st.session_state.usuario = ""
    st.session_state.reset_timer = True
    st.session_state.paso = "registro"
    st.rerun()

# PANTALLA: TRANSCRIPCIÓN GUARDADA (no se puede eliminar)
elif st.session_state.paso == "transcripcion":
    st.subheader("📄 Transcripción de la sesión")
    st.caption(f"Modo: {st.session_state.get('modo', '-')}  |  Alumno: {st.session_state.get('usuario', '-')}")

    if not st.session_state.mensajes:
        st.info("No hay conversación registrada en esta sesión.")
    else:
        # Mostramos el historial completo guardado
        for msj in st.session_state.mensajes:
            with st.chat_message(msj["role"]):
                st.markdown(msj["content"])

        # Texto plano para descargar / copiar
        texto_plano = "\n\n".join(
            [f"{'Alumno' if m['role']=='user' else 'Athena'}: {m['content']}" for m in st.session_state.mensajes]
        )
        st.download_button(
            "⬇️ Descargar transcripción (.txt)",
            data=texto_plano,
            file_name=f"transcripcion_{st.session_state.get('usuario','alumno')}.txt",
            mime="text/plain"
        )

    st.write(" ")
    if st.button("🏠 Volver al inicio"):
        # La transcripción queda archivada; NO se ofrece borrarla
        st.session_state.mensajes = []
        st.session_state.ultima_respuesta_ia = ""
        st.session_state.paso = "menu"
        st.rerun()

# PANTALLA: PANEL DEL PROFESOR (secreto, se entra escribiendo "system regist" en el nombre)
elif st.session_state.paso == "panel_admin":
    registros = cargar_registros()

    if not registros:
        st.info("Todavía no hay sesiones registradas.")
    else:
        st.caption(f"Total de sesiones guardadas: {len(registros)}")

        # Mostramos cada sesión en un desplegable
        for i, r in enumerate(reversed(registros), 1):
            titulo = f"{r.get('fecha','-')} — {r.get('nombre','-')} ({r.get('modo','-')})"
            with st.expander(titulo):
                st.markdown(f"**Nombre:** {r.get('nombre','-')}")
                st.markdown(f"**Correo:** {r.get('correo','-')}")
                st.markdown(f"**Grado:** {r.get('grado','-')}")
                st.markdown(f"**Opción elegida:** {r.get('modo','-')}")
                st.markdown(f"**Fecha:** {r.get('fecha','-')}")
                st.write("**Conversación:**")
                for m in r.get("mensajes", []):
                    with st.chat_message(m["role"]):
                        st.markdown(m["content"])

    st.write(" ")
    if st.button("🚪 Salir del panel"):
        st.session_state.paso = "registro"
        st.rerun()
