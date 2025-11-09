import streamlit as st
from openai import OpenAI
import pandas as pd
import plotly.graph_objects as go
import json
import io
import re
from collections import defaultdict

# ==========================================
# CONFIG GENERAL
# ==========================================
st.set_page_config(page_title="AI Workshop Assistant PRO", layout="wide")
st.title("🧩 AI Workshop Assistant — Process & Org Mapper")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==========================================
# IDIOMA + MODO
# ==========================================
lang = st.selectbox("🌍 Idioma / Language", ["Español", "English"])
mode = st.radio("🔧 Modo", ["Process Map", "Org Structure"], horizontal=True)

if lang == "Español":
    txt = {
        "intro_process": "Convierte la descripción o transcripción de un workshop en un **mapa de proceso por departamentos**, con pains y recomendaciones.",
        "intro_org": "Mapea la **estructura organizativa** de la empresa (grupo, subempresas, plantas, almacenes, departamentos...).",
        "input_label": "✏️ Pega aquí la descripción / transcripción:",
        "input_ph": "Ejemplo: Tenemos un grupo con 4 subempresas, cada una con 2 plantas de manufactura...",
        "btn_analyze": "🚀 Analizar con IA",
        "btn_redraw": "🔁 Redibujar sin volver a llamar a IA",
        "spinner": "Analizando con IA...",
        "warn_no_text": "Por favor introduce algo de texto.",
        "tab_map": "🗺️ Mapa visual",
        "tab_json": "📋 JSON estructurado",
        "tab_steps": "🧩 Pasos del proceso",
        "tab_depts": "🏢 Departamentos & actores",
        "tab_pains": "⚠️ Pain points",
        "tab_recs": "💡 Recomendaciones IA",
        "tab_export": "📤 Exportar a Excel",
        "tab_org_map": "🗺️ Org chart",
        "tab_org_json": "📋 JSON org",
        "tab_org_notes": "📝 Notas IA",
        "no_steps": "No se detectaron pasos.",
        "no_depts": "No se detectaron departamentos.",
        "no_actors": "No se detectaron actores.",
        "no_pains": "No se detectaron pain points.",
        "no_recs": "No se detectaron recomendaciones.",
        "no_org": "No se detectaron nodos organizativos.",
        "export_excel": "⬇️ Descargar Excel con análisis de proceso",
        "export_excel_org": "⬇️ Descargar Excel con estructura organizativa",
    }
else:
    txt = {
        "intro_process": "Turn a workshop transcript or process description into a **department-based process map**, with pains and AI recommendations.",
        "intro_org": "Map the company's **organizational structure** (group, subsidiaries, plants, warehouses, departments...).",
        "input_label": "✏️ Paste here the description / transcript:",
        "input_ph": "Example: We have a group with 4 subsidiaries, each with 2 manufacturing plants...",
        "btn_analyze": "🚀 Analyse with AI",
        "btn_redraw": "🔁 Redraw without calling AI",
        "spinner": "Analysing with AI...",
        "warn_no_text": "Please enter some text.",
        "tab_map": "🗺️ Visual map",
        "tab_json": "📋 Structured JSON",
        "tab_steps": "🧩 Process steps",
        "tab_depts": "🏢 Departments & actors",
        "tab_pains": "⚠️ Pain points",
        "tab_recs": "💡 AI recommendations",
        "tab_export": "📤 Export to Excel",
        "tab_org_map": "🗺️ Org chart",
        "tab_org_json": "📋 Org JSON",
        "tab_org_notes": "📝 AI notes",
        "no_steps": "No steps detected.",
        "no_depts": "No departments detected.",
        "no_actors": "No actors detected.",
        "no_pains": "No pain points detected.",
        "no_recs": "No recommendations detected.",
        "no_org": "No organizational nodes detected.",
        "export_excel": "⬇️ Download Excel with process analysis",
        "export_excel_org": "⬇️ Download Excel with org structure",
    }

st.markdown(txt["intro_process"] if mode == "Process Map" else txt["intro_org"])

# ==========================================
# SESSION STATE (MEMORIA TEMPORAL)
# ==========================================
if "process_data" not in st.session_state:
    st.session_state.process_data = None
if "org_data" not in st.session_state:
    st.session_state.org_data = None

# ==========================================
# INPUT
# ==========================================
user_text = st.text_area(
    txt["input_label"],
    placeholder=txt["input_ph"],
    height=220,
)

# ==========================================
# PROMPTS IA
# ==========================================
def get_process_system_prompt(lang: str) -> str:
    if lang == "Español":
        return """
Eres un consultor experto en procesos de negocio y BPMN.
A partir del texto (workshop, descripción), devuelve SOLO un JSON válido con esta estructura EXACTA:

{
  "steps": [
    {
      "name": "Nombre corto del paso",
      "description": "Descripción un poco más detallada",
      "actor": "Rol responsable principal",
      "department": "Departamento funcional (Sales, Manufacturing, Warehouse, Finance, HR, Quality, Logistics, Procurement, IT, Other)",
      "type": "start|task|decision|end",
      "options": [
        {
          "label": "Sí",
          "next": "Nombre del siguiente paso si se elige esta opción"
        }
      ]
    }
  ],
  "departments": ["Sales", "Manufacturing"],
  "actors": ["Production Planner", "Warehouse Operator"],
  "pains": [
    "Texto corto describiendo un problema"
  ],
  "recommendations": [
    {
      "area": "Departamento o ámbito",
      "recommendation": "Recomendación concreta de mejora",
      "impact": "High|Medium|Low"
    }
  ]
}

Reglas:
- Usa SIEMPRE esa estructura y claves exactas.
- El JSON debe ser válido, sin explicaciones ni texto alrededor.
- Detecta automáticamente departamentos en función del proceso (manufacturing, warehouse, finance, etc.).
- Si no hay decisiones, deja "options" como lista vacía o no la incluyas.
- Usa español en descripciones, pains y recomendaciones.
"""
    else:
        return """
You are an expert BPMN / business process consultant.
From the user's text (workshop / process description), return ONLY a valid JSON with this EXACT structure:

{
  "steps": [
    {
      "name": "Short step name",
      "description": "More detailed description of the step",
      "actor": "Main responsible role",
      "department": "Functional department (Sales, Manufacturing, Warehouse, Finance, HR, Quality, Logistics, Procurement, IT, Other)",
      "type": "start|task|decision|end",
      "options": [
        {
          "label": "Yes",
          "next": "Name of the next step if this option is chosen"
        }
      ]
    }
  ],
  "departments": ["Sales", "Manufacturing"],
  "actors": ["Production Planner", "Warehouse Operator"],
  "pains": [
    "Short description of a problem or pain"
  ],
  "recommendations": [
    {
      "area": "Department or area",
      "recommendation": "Concrete improvement recommendation",
      "impact": "High|Medium|Low"
    }
  ]
}

Rules:
- ALWAYS use that structure and those exact keys.
- JSON must be valid, with no extra text.
- Automatically infer departments from the described process.
- If there are no decisions, leave options empty or omit it.
- Use English for descriptions, pains and recommendations.
"""

def get_org_system_prompt(lang: str) -> str:
    if lang == "Español":
        return """
Eres un experto en diseño organizativo.
A partir del texto del usuario, devuelve SOLO un JSON válido con esta estructura:

{
  "nodes": [
    {
      "name": "Nombre de la entidad",
      "type": "group|holding|company|business_unit|plant|site|warehouse|department|team",
      "parent": "Nombre de la entidad padre o null si es la raíz"
    }
  ],
  "notes": [
    "Comentario breve sobre la estructura (opcional)"
  ]
}

Reglas:
- Usa SIEMPRE esa estructura y claves exactas.
- "parent" es el NOMBRE de otra entidad del array nodes, o null si es toplevel.
- Puedes tener varios niveles: grupo -> subempresas -> plantas -> almacenes -> departamentos -> equipos.
- No añadas texto fuera del JSON.
"""
    else:
        return """
You are an expert in organizational design.
From the user's text, return ONLY a valid JSON with this structure:

{
  "nodes": [
    {
      "name": "Entity name",
      "type": "group|holding|company|business_unit|plant|site|warehouse|department|team",
      "parent": "Name of parent entity or null if top-level"
    }
  ],
  "notes": [
    "Short comments about the structure (optional)"
  ]
}

Rules:
- ALWAYS use that structure and those exact keys.
- "parent" is the NAME of another entity in nodes, or null if it is top-level.
- You may have several levels: group -> subsidiaries -> plants -> warehouses -> departments -> teams.
- Do NOT add any text outside of the JSON.
"""

# ==========================================
# LLAMADAS A IA
# ==========================================
def call_openai_json(system_prompt: str, user_text: str):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    content = resp.choices[0].message.content.strip()
    # intentar parsear JSON directamente o extrayendo primer {...}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            return json.loads(m.group(0))
        else:
            raise ValueError("Respuesta de IA no contiene JSON válido.")


# ==========================================
# VISUALIZACIÓN: PROCESS SWIMLANES
# ==========================================
def draw_swimlane_diagram(steps):
    if not steps:
        return None

    # departamentos desde steps
    departments = []
    for s in steps:
        dept = s.get("department") or "Other"
        if dept not in departments:
            departments.append(dept)

    dept_to_y = {dept: -idx * 2 for idx, dept in enumerate(departments)}

    fig = go.Figure()

    # Colores por tipo
    type_colors = {
        "start": "#4CAF50",
        "end": "#37474F",
        "decision": "#FFB74D",
        "task": "#90CAF9"
    }

    # fondos de lanes
    x_min, x_max = 0, max(1, len(steps) * 2)
    for dept, y in dept_to_y.items():
        fig.add_shape(
            type="rect",
            x0=x_min - 0.5,
            y0=y - 0.8,
            x1=x_max + 0.5,
            y1=y + 0.8,
            line=dict(color="#DDDDDD", width=1),
            fillcolor="#F9F9F9",
            layer="below"
        )
        fig.add_annotation(
            x=x_min - 0.8,
            y=y,
            text=f"<b>{dept}</b>",
            showarrow=False,
            xanchor="right",
            font=dict(size=12, color="#555555")
        )

    # nodos
    node_pos = {}
    x = 0
    for idx, step in enumerate(steps):
        dept = step.get("department") or "Other"
        y = dept_to_y.get(dept, 0)
        node_id = f"S{idx}"

        step_type = (step.get("type") or "task").lower()
        color = type_colors.get(step_type, "#90CAF9")

        name = step.get("name", f"Step {idx+1}")
        actor = step.get("actor") or ""
        label = name
        if actor:
            label += f"<br><span style='font-size:11px;color:#333;'>{actor}</span>"

        # shape
        if step_type in ["start", "end"]:
            fig.add_shape(
                type="circle",
                x0=x,
                y0=y - 0.4,
                x1=x + 1.0,
                y1=y + 0.4,
                line=dict(color="#333333", width=1),
                fillcolor=color,
                layer="above",
            )
            center_x = x + 0.5
        elif step_type == "decision":
            # rombo aproximado: cuadrado rotado -> usamos annotation marker
            fig.add_shape(
                type="rect",
                x0=x,
                y0=y - 0.4,
                x1=x + 1.2,
                y1=y + 0.4,
                line=dict(color="#333333", width=1),
                fillcolor=color,
                layer="above",
            )
            center_x = x + 0.6
        else:
            fig.add_shape(
                type="rect",
                x0=x,
                y0=y - 0.4,
                x1=x + 1.8,
                y1=y + 0.4,
                line=dict(color="#333333", width=1),
                fillcolor=color,
                layer="above",
            )
            center_x = x + 0.9

        fig.add_annotation(
            x=center_x,
            y=y,
            text=label,
            showarrow=False,
            font=dict(size=11),
            align="center"
        )

        node_pos[node_id] = (center_x, y)
        x += 2

    # flechas secuenciales
    ids = list(node_pos.keys())
    for i in range(len(ids) - 1):
        x0, y0 = node_pos[ids[i]]
        x1, y1 = node_pos[ids[i + 1]]
        fig.add_annotation(
            x=x1 - 0.9,
            y=y1,
            ax=x0 + 0.9,
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

    # flechas de decisiones (ramas)
    name_to_pos = {}
    for idx, step in enumerate(steps):
        name_to_pos[step.get("name", f"Step {idx+1}")] = node_pos[f"S{idx}"]

    for step in steps:
        if isinstance(step.get("options"), list) and step["options"]:
            x0, y0 = name_to_pos.get(step["name"], (None, None))
            if x0 is None:
                continue
            for opt in step["options"]:
                target_name = opt.get("next")
                label = opt.get("label", "")
                if not target_name or target_name not in name_to_pos:
                    continue
                x1, y1 = name_to_pos[target_name]
                mid_x = (x0 + x1) / 2
                mid_y = (y0 + y1) / 2
                fig.add_annotation(
                    x=x1,
                    y=y1,
                    ax=x0,
                    ay=y0,
                    xref="x",
                    yref="y",
                    axref="x",
                    ayref="y",
                    showarrow=True,
                    arrowhead=3,
                    arrowsize=1,
                    arrowwidth=1.5,
                    arrowcolor="darkorange",
                )
                fig.add_annotation(
                    x=mid_x,
                    y=mid_y + 0.3,
                    text=label,
                    showarrow=False,
                    font=dict(size=10, color="darkorange"),
                )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        height=max(350, len(dept_to_y) * 150),
        plot_bgcolor="white",
        margin=dict(l=120, r=40, t=40, b=40),
    )

    return fig

# ==========================================
# VISUALIZACIÓN: ORG CHART
# ==========================================
def draw_org_chart(nodes):
    if not nodes:
        return None

    name_to_node = {n["name"]: n for n in nodes}
    # calcular niveles por recursión
    level_cache = {}

    def get_level(name):
        if name in level_cache:
            return level_cache[name]
        node = name_to_node.get(name, {})
        parent = node.get("parent")
        if not parent or parent not in name_to_node:
            level_cache[name] = 0
        else:
            level_cache[name] = get_level(parent) + 1
        return level_cache[name]

    levels = defaultdict(list)
    for n in nodes:
        lvl = get_level(n["name"])
        levels[lvl].append(n)

    fig = go.Figure()
    node_pos = {}

    # dibujar por niveles (arriba grupo, abajo plantas/departamentos)
    for lvl, items in levels.items():
        y = -lvl * 2
        for idx, node in enumerate(items):
            x = idx * 3
            name = node["name"]
            typ = node.get("type", "company")

            color_map = {
                "group": "#B39DDB",
                "holding": "#B39DDB",
                "company": "#90CAF9",
                "business_unit": "#80CBC4",
                "plant": "#FFE082",
                "site": "#FFE082",
                "warehouse": "#FFCC80",
                "department": "#C5E1A5",
                "team": "#F48FB1",
            }
            color = color_map.get(typ, "#E0E0E0")

            fig.add_shape(
                type="rect",
                x0=x,
                y0=y - 0.6,
                x1=x + 2.4,
                y1=y + 0.6,
                line=dict(color="#333333", width=1),
                fillcolor=color,
            )
            fig.add_annotation(
                x=x + 1.2,
                y=y,
                text=f"{name}<br><span style='font-size:11px;color:#333;'>{typ}</span>",
                showarrow=False,
                align="center",
                font=dict(size=11),
            )
            node_pos[name] = (x + 1.2, y)

    # conectar padres e hijos
    for node in nodes:
        parent = node.get("parent")
        if parent and parent in node_pos:
            x0, y0 = node_pos[parent]
            x1, y1 = node_pos[node["name"]]
            fig.add_annotation(
                x=x1,
                y=y1 + 0.6,
                ax=x0,
                ay=y0 - 0.6,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="gray",
            )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        height=max(350, len(levels) * 200),
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=40, b=40),
    )

    return fig

# ==========================================
# ACCIÓN: ANALIZAR CON IA
# ==========================================
col_btn1, col_btn2 = st.columns([2, 1])
pressed_analyze = col_btn1.button(txt["btn_analyze"])
pressed_redraw = col_btn2.button(txt["btn_redraw"])

if pressed_analyze:
    if not user_text.strip():
        st.warning(txt["warn_no_text"])
        st.stop()

    with st.spinner(txt["spinner"]):
        try:
            if mode == "Process Map":
                data = call_openai_json(get_process_system_prompt(lang), user_text)
                st.session_state.process_data = data
            else:
                data = call_openai_json(get_org_system_prompt(lang), user_text)
                st.session_state.org_data = data
        except Exception as e:
            st.error(f"Error llamando a la IA: {e}")
            st.stop()

if pressed_redraw:
    # solo redibuja usando los datos ya guardados
    pass

# ==========================================
# MOSTRAR RESULTADOS — PROCESS MODE
# ==========================================
if mode == "Process Map" and st.session_state.process_data:
    data = st.session_state.process_data
    steps = data.get("steps", []) or []
    departments = data.get("departments", []) or []
    actors = data.get("actors", []) or []
    pains = data.get("pains", []) or []
    recs = data.get("recommendations", []) or []

    tabs = st.tabs([
        txt["tab_map"],
        txt["tab_json"],
        txt["tab_steps"],
        txt["tab_depts"],
        txt["tab_pains"],
        txt["tab_recs"],
        txt["tab_export"],
    ])

    with tabs[0]:
        st.subheader(txt["tab_map"])
        if steps:
            fig = draw_swimlane_diagram(steps)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(txt["no_steps"])
        else:
            st.info(txt["no_steps"])

    with tabs[1]:
        st.subheader(txt["tab_json"])
        st.json(data)

    with tabs[2]:
        st.subheader(txt["tab_steps"])
        if steps:
            st.dataframe(pd.DataFrame(steps))
        else:
            st.info(txt["no_steps"])

    with tabs[3]:
        st.subheader(txt["tab_depts"])
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Departments**")
            if departments:
                st.dataframe(pd.DataFrame(departments, columns=["Department"]))
            else:
                st.info(txt["no_depts"])
        with c2:
            st.markdown("**Actors**")
            if actors:
                st.dataframe(pd.DataFrame(actors, columns=["Actor"]))
            else:
                st.info(txt["no_actors"])

    with tabs[4]:
        st.subheader(txt["tab_pains"])
        if pains:
            st.dataframe(pd.DataFrame(pains, columns=["Pain Point"]))
        else:
            st.info(txt["no_pains"])

    with tabs[5]:
        st.subheader(txt["tab_recs"])
        if recs:
            if isinstance(recs[0], dict):
                st.dataframe(pd.DataFrame(recs))
            else:
                st.dataframe(pd.DataFrame(recs, columns=["Recommendation"]))
        else:
            st.info(txt["no_recs"])

    with tabs[6]:
        st.subheader(txt["tab_export"])
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
            label=txt["export_excel"],
            data=buffer,
            file_name="process_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ==========================================
# MOSTRAR RESULTADOS — ORG MODE
# ==========================================
if mode == "Org Structure" and st.session_state.org_data:
    data = st.session_state.org_data
    nodes = data.get("nodes", []) or []
    notes = data.get("notes", []) or []

    tabs = st.tabs([txt["tab_org_map"], txt["tab_org_json"], txt["tab_org_notes"], txt["tab_export"]])

    with tabs[0]:
        st.subheader(txt["tab_org_map"])
        if nodes:
            fig = draw_org_chart(nodes)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(txt["no_org"])
        else:
            st.info(txt["no_org"])

    with tabs[1]:
        st.subheader(txt["tab_org_json"])
        st.json(data)

    with tabs[2]:
        st.subheader(txt["tab_org_notes"])
        if notes:
            st.write(notes)
        else:
            st.info("No notes.")

    with tabs[3]:
        st.subheader(txt["tab_export"])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            if nodes:
                pd.DataFrame(nodes).to_excel(writer, sheet_name="OrgNodes", index=False)
            if notes:
                pd.DataFrame(notes, columns=["Notes"]).to_excel(writer, sheet_name="Notes", index=False)
        buffer.seek(0)
        st.download_button(
            label=txt["export_excel_org"],
            data=buffer,
            file_name="org_structure.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
