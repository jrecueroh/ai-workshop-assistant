import streamlit as st
from openai import OpenAI
import pandas as pd
import plotly.graph_objects as go
import json
import io
import re
from collections import defaultdict

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
        "input_ph": "Ejemplo: Tenemos un grupo con 4 subempresas, cada una con 2 plantas de manufactura...",
        "analyze_btn": "🚀 Analizar empresa y procesos",
        "spinner": "Analizando con IA...",
        "warn_no_text": "Por favor introduce texto para analizar.",
        "tabs": [
            "🗺️ Mapa de Procesos",
            "🧩 Datos del Proceso",
            "🏗️ Estructura Organizacional",
            "📋 Datos Organizativos",
            "💡 Recomendaciones IA",
            "📤 Exportar"
        ],
        "no_data": "No se detectaron datos.",
        "export_label": "⬇️ Descargar Excel con toda la información"
    },
    "en": {
        "intro": "Analyze workshop descriptions or transcripts to automatically generate **processes and organizational structures**.",
        "input_label": "✏️ Paste the transcript or description here:",
        "input_ph": "Example: We have a group with 4 subsidiaries, each with 2 manufacturing plants...",
        "analyze_btn": "🚀 Analyze company and processes",
        "spinner": "Analyzing with AI...",
        "warn_no_text": "Please enter text to analyze.",
        "tabs": [
            "🗺️ Process Map",
            "🧩 Process Data",
            "🏗️ Organizational Structure",
            "📋 Org Data",
            "💡 AI Recommendations",
            "📤 Export"
        ],
        "no_data": "No data detected.",
        "export_label": "⬇️ Download Excel with all information"
    }
}[current_lang]

st.markdown(TXT["intro"])

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==============================
# INPUT
# ==============================
text = st.text_area(TXT["input_label"], placeholder=TXT["input_ph"], height=200)
analyze = st.button(TXT["analyze_btn"])

# ==============================
# PROMPT UNIFICADO
# ==============================
def unified_prompt(lang):
    if lang == "es":
        return """
Eres un consultor experto en procesos y diseño organizativo.
Del siguiente texto debes extraer **dos bloques JSON**: "organization" y "process".

Devuelve SOLO un JSON válido con esta estructura:

{
  "organization": {
    "nodes": [
      {"name": "Nombre", "type": "group|company|plant|department|team|warehouse|site", "parent": "Nombre del padre o null"}
    ],
    "notes": ["Comentarios breves sobre la estructura"]
  },
  "process": {
    "steps": [
      {"name": "Nombre del paso", "description": "Descripción breve", "actor": "Rol principal", "department": "Departamento funcional", "type": "start|task|decision|end", "options": [{"label": "Sí", "next": "Nombre del siguiente paso"}]}
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
From the following text, extract **two JSON blocks**: "organization" and "process".

Return ONLY a valid JSON with this structure:

{
  "organization": {
    "nodes": [
      {"name": "Name", "type": "group|company|plant|department|team|warehouse|site", "parent": "Parent name or null"}
    ],
    "notes": ["Short comments about the structure"]
  },
  "process": {
    "steps": [
      {"name": "Step name", "description": "Short description", "actor": "Main role", "department": "Functional department", "type": "start|task|decision|end", "options": [{"label": "Yes", "next": "Next step name"}]}
    ],
    "departments": ["Manufacturing", "Quality", "Finance"],
    "actors": ["Planner", "Operator"],
    "pains": ["Detected issue or bottleneck"],
    "recommendations": [{"area": "Manufacturing", "recommendation": "Automate quality inspection", "impact": "High"}]
  }
}
"""

# ==============================
# LLAMADA A LA IA (OPTIMIZADA)
# ==============================
def call_openai_json(system_prompt, user_text):
    try:
        # Primer intento con modelo rápido y barato
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
        # Fallback automático
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt + "\n\n⚠️ Devuelve solo JSON, breve y sin explicaciones."},
                {"role": "user", "content": user_text[:4000]},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        content = resp.choices[0].message.content.strip()

    # Buscar JSON válido
    match = re.search(r"\{.*\}", content, re.S)
    if match:
        json_text = match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            st.error("⚠️ JSON inválido recibido de la IA.")
            return {}
    else:
        st.error("⚠️ No se detectó JSON en la respuesta de la IA.")
        return {}

# ==============================
# VISUALIZACIONES
# ==============================
def draw_swimlane(steps):
    if not steps:
        return None
    depts = list({s.get("department", "Otro") for s in steps})
    dept_y = {d: -i * 2 for i, d in enumerate(depts)}
    fig = go.Figure()
    type_colors = {"start": "#4CAF50", "end": "#37474F", "decision": "#FFB74D", "task": "#90CAF9"}
    for d, y in dept_y.items():
        fig.add_shape(type="rect", x0=-1, y0=y-1, x1=len(steps)*2, y1=y+1,
                      fillcolor="#F9F9F9", line=dict(color="#DDD", width=1), layer="below")
        fig.add_annotation(x=-1.5, y=y, text=f"<b>{d}</b>", showarrow=False, xanchor="right")
    pos = {}
    for i, s in enumerate(steps):
        dept = s.get("department", "Otro")
        y = dept_y.get(dept, 0)
        color = type_colors.get(s.get("type", "task"), "#90CAF9")
        x0, x1 = i*2, i*2+1.5
        fig.add_shape(type="rect", x0=x0, y0=y-0.4, x1=x1, y1=y+0.4,
                      fillcolor=color, line=dict(color="#333", width=1))
        fig.add_annotation(x=x0+0.75, y=y, text=s["name"], showarrow=False)
        pos[s["name"]] = (x0+0.75, y)
    for i in range(len(steps)-1):
        x0, y0 = pos[steps[i]["name"]]
        x1, y1 = pos[steps[i+1]["name"]]
        fig.add_annotation(x=x1-0.8, y=y1, ax=x0+0.8, ay=y0, showarrow=True, arrowhead=3)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=max(400, len(depts)*150), plot_bgcolor="white")
    return fig


def draw_org(nodes):
    if not nodes:
        return None
    fig = go.Figure()
    lvls = defaultdict(list)
    for n in nodes:
        parent = n.get("parent")
        lvl = 0 if not parent else 1
        lvls[lvl].append(n)
    pos = {}
    for lvl, arr in lvls.items():
        for i, n in enumerate(arr):
            x, y = i*3, -lvl*3
            fig.add_shape(type="rect", x0=x, y0=y-0.6, x1=x+2.4, y1=y+0.6,
                          fillcolor="#E3F2FD", line=dict(color="#333", width=1))
            fig.add_annotation(x=x+1.2, y=y, text=n["name"], showarrow=False)
            pos[n["name"]] = (x+1.2, y)
    for n in nodes:
        p = n.get("parent")
        if p and p in pos:
            x0, y0 = pos[p]; x1, y1 = pos[n["name"]]
            fig.add_annotation(x=x1, y=y1+0.6, ax=x0, ay=y0-0.6, showarrow=True, arrowcolor="gray")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible(False)
    fig.update_layout(height=max(400, len(lvls)*200), plot_bgcolor="white")
    return fig

# ==============================
# ANÁLISIS
# ==============================
if analyze:
    if not text.strip():
        st.warning(TXT["warn_no_text"])
    else:
        with st.spinner(TXT["spinner"]):
            data = call_openai_json(unified_prompt(current_lang), text)
            st.session_state.company_data = data

# ==============================
# RESULTADOS
# ==============================
if "company_data" in st.session_state:
    d = st.session_state.company_data
    org = d.get("organization", {})
    proc = d.get("process", {})
    steps = proc.get("steps", [])
    pains = proc.get("pains", [])
    recs = proc.get("recommendations", [])
    nodes = org.get("nodes", [])
    notes = org.get("notes", [])

    tabs = st.tabs(TXT["tabs"])

    with tabs[0]:
        fig = draw_swimlane(steps)
        if fig: st.plotly_chart(fig, use_container_width=True)
        else: st.info(TXT["no_data"])

    with tabs[1]:
        st.json(proc)
        if steps: st.dataframe(pd.DataFrame(steps))
        if pains: st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))

    with tabs[2]:
        fig2 = draw_org(nodes)
        if fig2: st.plotly_chart(fig2, use_container_width=True)
        else: st.info(TXT["no_data"])

    with tabs[3]:
        st.json(org)
        if nodes: st.dataframe(pd.DataFrame(nodes))
        if notes: st.write(notes)

    with tabs[4]:
        if recs:
            df = pd.DataFrame(recs)
            st.dataframe(df)
        else:
            st.info(TXT["no_data"])

    with tabs[5]:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(steps).to_excel(writer, sheet_name="Steps", index=False)
            pd.DataFrame(pains).to_excel(writer, sheet_name="Pains", index=False)
            pd.DataFrame(recs).to_excel(writer, sheet_name="Recs", index=False)
            pd.DataFrame(nodes).to_excel(writer, sheet_name="OrgNodes", index=False)
        buffer.seek(0)
        st.download_button(
            label=TXT["export_label"],
            data=buffer,
            file_name="company_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
