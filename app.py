import streamlit as st
from openai import OpenAI
import pandas as pd
import plotly.graph_objects as go
import json
import io
import re

# ==========================================
# CONFIGURACIÓN BÁSICA
# ==========================================
st.set_page_config(page_title="AI Workshop Assistant — PRO", layout="wide")

st.title("🧩 AI Workshop Assistant — Process & Swimlane Mapper")

# Selector de idioma
lang = st.selectbox("🌍 Idioma / Language", ["Español", "English"])

if lang == "Español":
    ui = {
        "intro": "Convierte la transcripción de un workshop o descripción de procesos en un mapa visual por departamentos, con análisis y recomendaciones de IA.",
        "textarea_label": "✏️ Pega aquí la descripción o transcripción del proceso",
        "textarea_ph": "Ejemplo: Tenemos cuatro plantas de producción, logística gestiona el almacén, finanzas valida facturas...",
        "button_analyze": "🚀 Analizar y generar mapa",
        "warn_no_text": "Por favor, introduce una descripción del proceso.",
        "spinner": "Analizando el proceso con IA...",
        "tab_map": "🗺️ Mapa visual",
        "tab_json": "📋 JSON estructurado",
        "tab_steps": "🧩 Pasos del proceso",
        "tab_depts": "🏢 Departamentos y actores",
        "tab_pains": "⚠️ Pain points",
        "tab_recs": "💡 Recomendaciones IA",
        "tab_export": "📤 Exportar",
        "no_steps": "No se detectaron pasos para graficar.",
        "no_depts": "No se detectaron departamentos.",
        "no_actors": "No se detectaron actores.",
        "no_pains": "No se detectaron pain points.",
        "no_recs": "No se detectaron recomendaciones.",
        "export_excel": "⬇️ Descargar Excel",
        "excel_name": "process_analysis.xlsx",
    }
    system_prompt = """
Eres un consultor experto en procesos de negocio y BPMN.
A partir del texto del usuario (workshop, descripción de procesos), devuelve SOLO un JSON válido con esta estructura EXACTA:

{
  "steps": [
    {
      "name": "Nombre corto del paso",
      "description": "Descripción algo más detallada del paso",
      "actor": "Rol principal responsable (ej. Production Planner, Warehouse Operator, AR Accountant)",
      "department": "Departamento funcional (ej. Manufacturing, Warehouse, Sales, Finance, HR, Quality, Logistics, Procurement, IT)",
      "type": "start|task|decision|end"
    }
  ],
  "departments": ["Manufacturing", "Warehouse", "Sales"],
  "actors": ["Production Planner", "Warehouse Operator"],
  "pains": [
    "Descripción corta de un problema o dolor detectado"
  ],
  "recommendations": [
    {
      "area": "Departamento o ámbito (ej. Manufacturing, Finance)",
      "recommendation": "Recomendación concreta de mejora",
      "impact": "High|Medium|Low"
    }
  ]
}

Reglas:
- Usa SIEMPRE esa estructura y claves exactamente.
- El JSON debe ser VALIDO (sin texto extra).
- Detecta automáticamente departamentos a partir del contexto real (manufacturing, warehouse, finance, sales, etc.).
- Usa español para descripciones, pains y recomendaciones.
"""
else:
    ui = {
        "intro": "Turn a workshop transcript or process description into a department-based visual map, with AI analysis and recommendations.",
        "textarea_label": "✏️ Paste here the process description or workshop transcript",
        "textarea_ph": "Example: We have four manufacturing plants, warehouse handles inventory, finance validates invoices...",
        "button_analyze": "🚀 Analyse and generate map",
        "warn_no_text": "Please enter a process description.",
        "spinner": "Analysing process with AI...",
        "tab_map": "🗺️ Visual map",
        "tab_json": "📋 Structured JSON",
        "tab_steps": "🧩 Process steps",
        "tab_depts": "🏢 Departments & actors",
        "tab_pains": "⚠️ Pain points",
        "tab_recs": "💡 AI recommendations",
        "tab_export": "📤 Export",
        "no_steps": "No steps detected to plot.",
        "no_depts": "No departments detected.",
        "no_actors": "No actors detected.",
        "no_pains": "No pain points detected.",
        "no_recs": "No recommendations detected.",
        "export_excel": "⬇️ Download Excel",
        "excel_name": "process_analysis.xlsx",
    }
    system_prompt = """
You are an expert business process and BPMN consultant.
From the user's text (workshop, process description), return ONLY a valid JSON with this EXACT structure:

{
  "steps": [
    {
      "name": "Short step name",
      "description": "More detailed description of the step",
      "actor": "Main responsible role (e.g. Production Planner, Warehouse Operator, AR Accountant)",
      "department": "Functional department (e.g. Manufacturing, Warehouse, Sales, Finance, HR, Quality, Logistics, Procurement, IT)",
      "type": "start|task|decision|end"
    }
  ],
  "departments": ["Manufacturing", "Warehouse", "Sales"],
  "actors": ["Production Planner", "Warehouse Operator"],
  "pains": [
    "Short description of a pain or issue detected"
  ],
  "recommendations": [
    {
      "area": "Department or area (e.g. Manufacturing, Finance)",
      "recommendation": "Concrete improvement recommendation",
      "impact": "High|Medium|Low"
    }
  ]
}

Rules:
- ALWAYS use that structure and those exact keys.
- JSON must be VALID (no extra text).
- Automatically detect departments from the real context (manufacturing, warehouse, finance, sales, etc.).
- Use English for descriptions, pains and recommendations.
"""

st.markdown(ui["intro"])

# OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==========================================
# ENTRADA DE USUARIO
# ==========================================
user_text = st.text_area(
    ui["textarea_label"],
    placeholder=ui["textarea_ph"],
    height=220,
)

# ==========================================
# FUNCIÓN: DIBUJAR SWIMLANES
# ==========================================
def draw_swimlane_diagram(steps):
    if not steps:
        return None

    # Obtener departamentos únicos a partir de los steps
    departments = []
    for s in steps:
        dept = s.get("department") or "Other"
        if dept not in departments:
            departments.append(dept)

    # Asignar una fila (y) por departamento
    dept_to_y = {dept: -idx * 2 for idx, dept in enumerate(departments)}  # filas negativas para que crezca hacia abajo

    fig = go.Figure()

    # Colores por tipo
    type_colors = {
        "start": "#4CAF50",
        "end": "#37474F",
        "decision": "#FFB74D",
        "task": "#90CAF9"
    }

    # Dibujar fondo de cada swimlane
    x_min, x_max = 0, max(1, len(steps) * 2)
    for dept, y in dept_to_y.items():
        fig.add_shape(
            type="rect",
            x0=x_min - 0.5,
            y0=y - 0.8,
            x1=x_max + 0.5,
            y1=y + 0.8,
            line=dict(color="#CCCCCC", width=1),
            fillcolor="#F9F9F9",
            layer="below"
        )
        fig.add_annotation(
            x=x_min - 0.8,
            y=y,
            text=f"<b>{dept}</b>",
            showarrow=False,
            xanchor="right",
            font=dict(size=12)
        )

    # Posiciones de cada step
    node_positions = {}
    x = 0
    for idx, step in enumerate(steps):
        dept = step.get("department") or "Other"
        y = dept_to_y.get(dept, 0)
        node_id = f"S{idx}"

        step_type = (step.get("type") or "task").lower()
        color = type_colors.get(step_type, "#90CAF9")

        label = step.get("name", f"Step {idx+1}")
        actor = step.get("actor") or ""
        if actor:
            label += f"<br><span style='font-size:11px;color:#333;'>{actor}</span>"

        # Nodo (rectángulo)
        fig.add_shape(
            type="rect",
            x0=x,
            y0=y - 0.4,
            x1=x + 1.6,
            y1=y + 0.4,
            line=dict(color="#333333", width=1),
            fillcolor=color,
            layer="above"
        )
        fig.add_annotation(
            x=x + 0.8,
            y=y,
            text=label,
            showarrow=False,
            font=dict(size=11),
            align="center"
        )

        node_positions[node_id] = (x, y)
        x += 2

    # Flechas entre pasos consecutivos
    ids = list(node_positions.keys())
    for i in range(len(ids) - 1):
        x0, y0 = node_positions[ids[i]]
        x1, y1 = node_positions[ids[i + 1]]
        fig.add_annotation(
            x=x1,
            y=y1,
            ax=x0 + 1.6,
            ay=y0,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="gray",
        )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        height=max(300, len(departments) * 150),
        plot_bgcolor="white",
        margin=dict(l=120, r=40, t=40, b=40),
    )

    return fig

# ==========================================
# BOTÓN PRINCIPAL
# ==========================================
if st.button(ui["button_analyze"]):
    if not user_text.strip():
        st.warning(ui["warn_no_text"])
        st.stop()

    with st.spinner(ui["spinner"]):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
            )
            content = resp.choices[0].message.content.strip()

            # Intentar parsear JSON directo o extrayendo el primer {...}
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                m = re.search(r"\{.*\}", content, re.S)
                if m:
                    data = json.loads(m.group(0))
                else:
                    st.error("La IA no devolvió JSON válido. Salida cruda:")
                    st.code(content)
                    st.stop()

            steps = data.get("steps", []) or []
            departments = data.get("departments", []) or []
            actors = data.get("actors", []) or []
            pains = data.get("pains", []) or []
            recs = data.get("recommendations", []) or []

            tabs = st.tabs([
                ui["tab_map"],
                ui["tab_json"],
                ui["tab_steps"],
                ui["tab_depts"],
                ui["tab_pains"],
                ui["tab_recs"],
                ui["tab_export"],
            ])

            # 🗺️ MAPA VISUAL
            with tabs[0]:
                st.subheader(ui["tab_map"])
                if steps:
                    fig = draw_swimlane_diagram(steps)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(ui["no_steps"])
                else:
                    st.info(ui["no_steps"])

            # 📋 JSON
            with tabs[1]:
                st.subheader(ui["tab_json"])
                st.json(data)

            # 🧩 PASOS
            with tabs[2]:
                st.subheader(ui["tab_steps"])
                if steps:
                    st.dataframe(pd.DataFrame(steps))
                else:
                    st.info(ui["no_steps"])

            # 🏢 DEPARTAMENTOS & ACTORES
            with tabs[3]:
                st.subheader(ui["tab_depts"])
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Departments**")
                    if departments:
                        st.dataframe(pd.DataFrame(departments, columns=["Department"]))
                    else:
                        st.info(ui["no_depts"])
                with col2:
                    st.markdown("**Actors**")
                    if actors:
                        st.dataframe(pd.DataFrame(actors, columns=["Actor"]))
                    else:
                        st.info(ui["no_actors"])

            # ⚠️ PAINS
            with tabs[4]:
                st.subheader(ui["tab_pains"])
                if pains:
                    st.dataframe(pd.DataFrame(pains, columns=["Pain Point"]))
                else:
                    st.info(ui["no_pains"])

            # 💡 RECOMMENDATIONS
            with tabs[5]:
                st.subheader(ui["tab_recs"])
                if recs:
                    # Si vienen como dicts
                    if isinstance(recs[0], dict):
                        st.dataframe(pd.DataFrame(recs))
                    else:
                        st.dataframe(pd.DataFrame(recs, columns=["Recommendation"]))
                else:
                    st.info(ui["no_recs"])

            # 📤 EXPORTAR
            with tabs[6]:
                st.subheader(ui["tab_export"])
                # Construir Excel en memoria
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    if steps:
                        pd.DataFrame(steps).to_excel(writer, sheet_name="Steps", index=False)
                    if pains:
                        pd.DataFrame(pains, columns=["Pain Point"]).to_excel(writer, sheet_name="Pains", index=False)
                    if recs:
                        if isinstance(recs[0], dict):
                            pd.DataFrame(recs).to_excel(writer, sheet_name="Recommendations", index=False)
                        else:
                            pd.DataFrame(recs, columns=["Recommendation"]).to_excel(writer, sheet_name="Recommendations", index=False)
                    if departments:
                        pd.DataFrame(departments, columns=["Department"]).to_excel(writer, sheet_name="Departments", index=False)
                    if actors:
                        pd.DataFrame(actors, columns=["Actor"]).to_excel(writer, sheet_name="Actors", index=False)

                buffer.seek(0)
                st.download_button(
                    label=ui["export_excel"],
                    data=buffer,
                    file_name=ui["excel_name"],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Error en el análisis o llamada a la API: {e}")
