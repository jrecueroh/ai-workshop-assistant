import streamlit as st
from openai import OpenAI
import pandas as pd
import graphviz
import json
import io
import re
from collections import defaultdict
import streamlit.components.v1 as components

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(page_title="AI Workshop Assistant PRO", layout="wide")

# ==============================
# ESTILO CSS
# ==============================
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
        text-align: right;
    }
    button[role="button"] {
        border-radius: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================
# ESTADO DE IDIOMA
# ==============================
if "lang" not in st.session_state:
    st.session_state.lang = "es"  # Español por defecto

# ==============================
# TOP BAR CON BANDERA
# ==============================
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("## 🧩 AI Workshop Assistant PRO")
with col2:
    if st.session_state.lang == "es":
        if st.button("🇬🇧", help="Switch to English"):
            st.session_state.lang = "en"
            st.rerun()
    else:
        if st.button("🇪🇸", help="Cambiar a Español"):
            st.session_state.lang = "es"
            st.rerun()

current_lang = st.session_state.lang

# ==============================
# TEXTOS
# ==============================
TXT = {
    "es": {
        "intro": "Analiza descripciones o transcripciones de workshops para generar **procesos y estructuras organizacionales** automáticamente.",
        "input_label": "✏️ Pega aquí la transcripción o descripción:",
        "input_ph": "Ejemplo: Matías: necesitamos revisar el flujo de producción. Sofía: el control de calidad tarda demasiado...",
        "analyze_btn": "🚀 Analizar empresa y procesos",
        "spinner": "Analizando con IA...",
        "warn_no_text": "Por favor introduce texto para analizar.",
        "tabs": [
            "🗺️ Mapa de Procesos",
            "🏗️ Estructura Organizacional",
            "🧩 Datos del Proceso",
            "📋 Datos Organizativos",
            "👥 Participantes",
            "💡 Recomendaciones IA",
            "📤 Exportar"
        ],
        "no_data": "No se detectaron datos.",
        "export_label": "⬇️ Descargar Excel con toda la información"
    },
    "en": {
        "intro": "Analyze workshop descriptions or transcripts to automatically generate **processes and organizational structures**.",
        "input_label": "✏️ Paste the transcript or description here:",
        "input_ph": "Example: Matías: we need to review the production flow. Sofía: quality control takes too long...",
        "analyze_btn": "🚀 Analyze company and processes",
        "spinner": "Analyzing with AI...",
        "warn_no_text": "Please enter text to analyze.",
        "tabs": [
            "🗺️ Process Map",
            "🏗️ Organizational Structure",
            "🧩 Process Data",
            "📋 Org Data",
            "👥 Participants",
            "💡 AI Recommendations",
            "📤 Export"
        ],
        "no_data": "No data detected.",
        "export_label": "⬇️ Download Excel with all information"
    }
}[current_lang]

st.markdown(TXT["intro"])

# ==============================
# CLIENTE OPENAI
# ==============================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==============================
# INPUT
# ==============================
text = st.text_area(TXT["input_label"], placeholder=TXT["input_ph"], height=200)
analyze = st.button(TXT["analyze_btn"])

# ==============================
# PREPROCESAR TRANSCRIPCIÓN
# ==============================
def preprocess_transcript(text):
    speakers = re.findall(r"(\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+):", text)
    unique = list(set(speakers))
    clean_text = re.sub(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+:\s*", "", text)
    return {
        "unique_speakers": unique,
        "clean_text": clean_text.strip()
    }

# ==============================
# PROMPT UNIFICADO
# ==============================
def unified_prompt(lang):
    if lang == "es":
        return """
Eres un consultor experto en procesos y diseño organizativo.
Del siguiente texto debes extraer **tres bloques JSON**: "organization", "process" y "participants".

Si hay nombres de personas (por ejemplo “Matías:” o “Sofía:”), debes incluirlas en "participants" indicando su rol inferido.

Devuelve SOLO un JSON válido con esta estructura:

{
  "participants": [
    {"name": "Matías", "role": "Planner o similar"}
  ],
  "organization": {
    "nodes": [
      {"name": "Nombre", "type": "group|company|plant|department|team|warehouse|site", "parent": "Nombre del padre o null"}
    ],
    "notes": ["Comentarios breves sobre la estructura"]
  },
  "process": {
    "steps": [
      {"name": "Nombre del paso", "description": "Descripción breve", "actor": "Rol principal", "department": "Departamento funcional", "type": "start|task|decision|end"}
    ],
    "departments": ["Manufacturing", "Quality", "Finance"],
    "actors": ["Planner", "Operator"],
    "pains": ["Problema o dificultad detectada"],
    "recommendations": [{"area": "Manufacturing", "recommendation": "Automatizar inspección de calidad", "impact": "High"}]
  }
}
"""
    else:
        return """
You are a consultant expert in business processes and organizational design.
From the following text, extract **three JSON blocks**: "organization", "process" and "participants".

If names like “Matías:” or “Sofía:” appear, include them in "participants" with inferred functional roles.

Return ONLY a valid JSON with this structure:

{
  "participants": [
    {"name": "Matías", "role": "Planner or similar"}
  ],
  "organization": {
    "nodes": [
      {"name": "Name", "type": "group|company|plant|department|team|warehouse|site", "parent": "Parent or null"}
    ],
    "notes": ["Short comments about the structure"]
  },
  "process": {
    "steps": [
      {"name": "Step name", "description": "Short description", "actor": "Main role", "department": "Functional department", "type": "start|task|decision|end"}
    ],
    "departments": ["Manufacturing", "Quality", "Finance"],
    "actors": ["Planner", "Operator"],
    "pains": ["Detected issue or bottleneck"],
    "recommendations": [{"area": "Manufacturing", "recommendation": "Automate quality inspection", "impact": "High"}]
  }
}
"""

# ==============================
# LLAMADA A OPENAI
# ==============================
def call_openai_json(system_prompt, user_text):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt + "\n\n⚠️ Devuelve solo JSON, breve y sin explicaciones."},
                {"role": "user", "content": user_text[:4000]},
            ],
            temperature=0.3,
            max_tokens=1200,
            timeout=40,
        )
        content = resp.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"⚠️ Error con gpt-4o-mini ({e}), usando gpt-3.5-turbo.")
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text[:4000]},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        content = resp.choices[0].message.content.strip()

    match = re.search(r"\{.*\}", content, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            st.error("⚠️ JSON inválido recibido de la IA.")
            return {}
    else:
        st.error("⚠️ No se detectó JSON en la respuesta de la IA.")
        return {}

# ==============================
# NUEVAS VISUALIZACIONES (GRAPHVIZ)
# ==============================
def draw_process_graphviz(steps):
    if not steps:
        return None
    dot = graphviz.Digraph(format="svg")
    dot.attr(rankdir="LR", splines="ortho", nodesep="1.0", ranksep="0.8", bgcolor="white")
    for s in steps:
        node_type = s.get("type", "task")
        color = {
            "start": "#4CAF50",
            "task": "#2196F3",
            "decision": "#FFC107",
            "end": "#455A64"
        }.get(node_type, "#90A4AE")
        shape = {
            "start": "circle",
            "task": "box",
            "decision": "diamond",
            "end": "doublecircle"
        }.get(node_type, "box")
        label = f"{s['name']}\n({s.get('actor','')})"
        dot.node(s["name"], label, shape=shape, style="filled", fillcolor=color, fontcolor="white")
    for i in range(len(steps) - 1):
        dot.edge(steps[i]["name"], steps[i + 1]["name"], arrowhead="vee", color="#555")
    return dot.pipe().decode("utf-8")

def draw_org_graphviz(nodes):
    if not nodes:
        return None
    dot = graphviz.Digraph(format="svg")
    dot.attr(rankdir="TB", nodesep="0.8", ranksep="0.9", bgcolor="white")
    for n in nodes:
        color = {
            "group": "#B39DDB",
            "company": "#90CAF9",
            "plant": "#A5D6A7",
            "department": "#FFF59D",
            "team": "#FFCC80"
        }.get(n["type"], "#E0E0E0")
        dot.node(n["name"], n["name"], shape="box", style="filled", fillcolor=color)
    for n in nodes:
        if n.get("parent"):
            dot.edge(n["parent"], n["name"], color="#555")
    return dot.pipe().decode("utf-8")

# ==============================
# ANÁLISIS
# ==============================
if "analyze" not in locals():
    analyze = False

if analyze:
    if not text.strip():
        st.warning(TXT["warn_no_text"])
    else:
        with st.spinner(TXT["spinner"]):
            pre = preprocess_transcript(text)
            prompt = unified_prompt(current_lang)
            data = call_openai_json(prompt, pre["clean_text"])
            data["participants"] = data.get("participants", []) + [
                {"name": p, "role": "Por inferir"} for p in pre["unique_speakers"]
                if p not in [x.get("name") for x in data.get("participants", [])]
            ]
            st.session_state.company_data = data

# ==============================
# RESULTADOS
# ==============================
if "company_data" in st.session_state:
    d = st.session_state.company_data
    org = d.get("organization", {})
    proc = d.get("process", {})
    parts = d.get("participants", [])
    steps = proc.get("steps", [])
    pains = proc.get("pains", [])
    recs = proc.get("recommendations", [])
    nodes = org.get("nodes", [])
    notes = org.get("notes", [])

    tabs = st.tabs(TXT["tabs"])

    with tabs[0]:
        svg = draw_process_graphviz(steps)
        if svg:
            components.html(svg, height=600, scrolling=True)
        else:
            st.info(TXT["no_data"])

    with tabs[1]:
        svg2 = draw_org_graphviz(nodes)
        if svg2:
            components.html(svg2, height=600, scrolling=True)
        else:
            st.info(TXT["no_data"])

    with tabs[2]:
        st.json(proc)
        if steps:
            st.dataframe(pd.DataFrame(steps))
        if pains:
            st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))

    with tabs[3]:
        st.json(org)
        if nodes:
            st.dataframe(pd.DataFrame(nodes))
        if notes:
            st.write(notes)

    with tabs[4]:
        if parts:
            st.dataframe(pd.DataFrame(parts))
        else:
            st.info("No se detectaron hablantes o participantes.")

    with tabs[5]:
        if recs:
            st.dataframe(pd.DataFrame(recs))
        else:
            st.info(TXT["no_data"])

    with tabs[6]:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(steps).to_excel(writer, sheet_name="Steps", index=False)
            pd.DataFrame(pains).to_excel(writer, sheet_name="Pains", index=False)
            pd.DataFrame(recs).to_excel(writer, sheet_name="Recs", index=False)
            pd.DataFrame(nodes).to_excel(writer, sheet_name="OrgNodes", index=False)
            pd.DataFrame(parts).to_excel(writer, sheet_name="Participants", index=False)
        buffer.seek(0)
        st.download_button(
            label=TXT["export_label"],
            data=buffer,
            file_name="company_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

