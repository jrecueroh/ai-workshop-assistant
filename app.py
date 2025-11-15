import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import re
import io
import streamlit.components.v1 as components

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(page_title="AI Workshop Assistant PRO", layout="wide")

st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {text-align:right;}
    button[role="button"] {border-radius:12px!important;}
    .main {font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================
# IDIOMA
# ==============================
if "lang" not in st.session_state:
    st.session_state.lang = "es"

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

lang = st.session_state.lang

# ==============================
# TEXTOS
# ==============================
TXT = {
    "es": {
        "intro": "Analiza descripciones o transcripciones de workshops para generar **procesos y estructuras organizacionales** automáticamente.",
        "input_label": "✏️ Pega aquí la transcripción o descripción:",
        "input_ph": "Ejemplo: Matías: el cliente hace un pedido. Sofía: se revisa la orden...",
        "analyze_btn": "🚀 Analizar empresa y procesos",
        "spinner": "Analizando con IA...",
        "warn_no_text": "Por favor introduce texto para analizar.",
        "tabs": [
            "🗺️ Mapa de Procesos",
            "🧩 Datos del Proceso",
            "🏗️ Estructura Organizacional",
            "📋 Datos Organizativos",
            "👥 Participantes",
            "💡 Recomendaciones IA",
            "📤 Exportar",
        ],
        "no_data": "No se detectaron datos.",
        "export_label": "⬇️ Descargar Excel con toda la información",
    },
    "en": {
        "intro": "Analyze workshop transcripts to automatically build **process and org structures**.",
        "input_label": "✏️ Paste transcript or description:",
        "input_ph": "Example: Matías: client places an order. Sofía: quality reviews the batch...",
        "analyze_btn": "🚀 Analyze company and processes",
        "spinner": "Analyzing with AI...",
        "warn_no_text": "Please enter text to analyze.",
        "tabs": [
            "🗺️ Process Map",
            "🧩 Process Data",
            "🏗️ Org Structure",
            "📋 Org Data",
            "👥 Participants",
            "💡 AI Recommendations",
            "📤 Export",
        ],
        "no_data": "No data detected.",
        "export_label": "⬇️ Download Excel with all information",
    },
}[lang]

st.markdown(TXT["intro"])

# ==============================
# OPENAI CLIENT
# ==============================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==============================
# INPUT
# ==============================
text = st.text_area(
    TXT["input_label"], placeholder=TXT["input_ph"], height=200, key="main_text"
)
analyze = st.button(TXT["analyze_btn"])


# ==============================
# HELPERS
# ==============================
def preprocess_transcript(t: str):
    """
    Detecta nombres tipo 'Matías:' y devuelve:
    - lista de speakers
    - texto limpio sin los 'Nombre:'
    """
    speakers = re.findall(r"(\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+):", t)
    clean = re.sub(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+:\s*", "", t)
    return {"speakers": list(set(speakers)), "text": clean.strip()}


def unified_prompt(current_lang: str) -> str:
    if current_lang == "es":
        return """
Eres un consultor experto en procesos y diseño organizativo.

Del siguiente texto debes extraer TRES bloques JSON:
1) "organization"
2) "process"
3) "participants"

Devuelve SOLO un JSON válido con esta estructura (ejemplo):

{
  "organization": {
    "nodes": [
      {"name": "Grupo Central", "type": "group", "parent": null},
      {"name": "Planta Norte", "type": "plant", "parent": "Grupo Central"},
      {"name": "Producción", "type": "department", "parent": "Planta Norte"}
    ],
    "notes": ["Estructura jerárquica básica con plantas y departamentos."]
  },
  "process": {
    "steps": [
      {"name": "Inicio pedido", "description": "El cliente realiza el pedido", "department": "Ventas", "type": "start"},
      {"name": "Registro de orden", "description": "Se registra en el sistema", "department": "Ventas", "type": "task"},
      {"name": "Fabricación del producto", "description": "Se produce el lote", "department": "Producción", "type": "task"},
      {"name": "Control de inspección", "description": "Calidad revisa el lote", "department": "Calidad", "type": "task"},
      {"name": "Fin", "description": "Pedido cerrado", "department": "Ventas", "type": "end"}
    ],
    "departments": ["Ventas", "Producción", "Calidad"],
    "pains": ["Retrasos en control de calidad"],
    "recommendations": [
      {"area": "Calidad", "recommendation": "Automatizar parte de la inspección", "impact": "High"}
    ]
  },
  "participants": ["Matías", "Sofía", "Carlos"]
}

- Los nombres de personas van SOLO en "participants".
- En los pasos de proceso NO pongas los nombres de personas, solo el departamento/actividad.
- Asegúrate de que 'parent' siempre usa el CAMPO 'name' de otro nodo o null.
"""
    else:
        return """
You are a consultant expert in business processes and organizational design.

From the text, extract THREE JSON blocks:
1) "organization"
2) "process"
3) "participants"

Return ONLY valid JSON with this structure (example):

{
  "organization": {
    "nodes": [
      {"name": "Head Group", "type": "group", "parent": null},
      {"name": "Plant North", "type": "plant", "parent": "Head Group"},
      {"name": "Manufacturing", "type": "department", "parent": "Plant North"}
    ],
    "notes": ["Hierarchical group with plants and departments."]
  },
  "process": {
    "steps": [
      {"name": "Order start", "description": "Customer places order", "department": "Sales", "type": "start"},
      {"name": "Register order", "description": "Order is registered", "department": "Sales", "type": "task"},
      {"name": "Manufacture product", "description": "Batch is produced", "department": "Manufacturing", "type": "task"},
      {"name": "Quality inspection", "description": "Quality reviews batch", "department": "Quality", "type": "task"},
      {"name": "End", "description": "Order closed", "department": "Sales", "type": "end"}
    ],
    "departments": ["Sales", "Manufacturing", "Quality"],
    "pains": ["Delays in inspection"],
    "recommendations": [
      {"area": "Quality", "recommendation": "Automate part of QC", "impact": "High"}
    ]
  },
  "participants": ["Matías", "Sofía", "Carlos"]
}

- Person names must go ONLY in "participants".
- Process steps MUST NOT include people names; only department/activity.
- 'parent' must always reference the 'name' of another node, or null.
"""


def call_openai_json(system_prompt: str, user_text: str):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                    + "\n\n⚠️ Devuelve solo JSON, sin explicaciones alrededor.",
                },
                {"role": "user", "content": user_text[:4000]},
            ],
            temperature=0.2,
            max_tokens=1200,
            timeout=40,
        )
        content = resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error llamando a OpenAI: {e}")
        return {}

    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        st.error("⚠️ La IA no devolvió JSON.")
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        st.error("⚠️ JSON inválido recibido de la IA.")
        return {}


def sanitize_label(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace('"', "")
        .replace("'", "")
        .replace("\n", " ")
        .strip()
    )


# ==============================
# VISUALIZACIÓN: MAPA DE PROCESOS (MERMAID)
# ==============================
def draw_process_mermaid(steps):
    if not steps:
        return None

    # departamentos únicos
    departments = []
    for s in steps:
        d = s.get("department") or "General"
        if d not in departments:
            departments.append(d)

    node_dept = {}
    mermaid = "flowchart LR\n"

    # lanes por departamento (Mermaid subgraph)
    for dept in departments:
        mermaid += f"  subgraph {sanitize_label(dept)}\n"
        for s in [x for x in steps if (x.get("department") or "General") == dept]:
            idx = steps.index(s)
            name = sanitize_label(s.get("name", f"Paso {idx+1}"))
            node_type = s.get("type", "task")

            if node_type == "start":
                node_def = f'N{idx}(["{name}"]):::startNode'
            elif node_type == "end":
                node_def = f'N{idx}(["{name}"]):::endNode'
            elif node_type == "decision":
                node_def = f'N{idx}{{"{name}"}}:::decisionNode'
            else:
                node_def = f'N{idx}["{name}"]:::taskNode'

            mermaid += f"    {node_def}\n"
            node_dept[idx] = dept
        mermaid += "  end\n\n"

    # conexiones en orden
    for i in range(len(steps) - 1):
        if node_dept.get(i) != node_dept.get(i + 1):
            mermaid += f"  N{i} -.-> N{i+1}\n"
        else:
            mermaid += f"  N{i} --> N{i+1}\n"

    # estilos
    mermaid += """
    classDef startNode fill:#C8E6C9,stroke:#2E7D32,stroke-width:3px,color:#000,font-size:20px,font-weight:bold;
    classDef endNode fill:#FFCDD2,stroke:#B71C1C,stroke-width:3px,color:#000,font-size:20px,font-weight:bold;
    classDef decisionNode fill:#FFF9C4,stroke:#F57F17,stroke-width:3px,color:#000,font-size:20px,font-weight:bold;
    classDef taskNode fill:#E3F2FD,stroke:#1565C0,stroke-width:2.5px,color:#000,font-size:20px,font-weight:bold;
    linkStyle default stroke-width:2.5px;
    """

    html = f"""
    <div id="graph-container" style="position:relative;width:100%;height:900px;overflow:hidden;border:1px solid #ddd;">
      <div id="zoom-controls" style="
          position:absolute;top:10px;right:10px;z-index:20;
          background:rgba(255,255,255,0.95);padding:5px 10px;border-radius:8px;
          box-shadow:0 1px 3px rgba(0,0,0,0.3);font-size:18px;">
        🔍 <button onclick="zoomIn()">+</button>
        <button onclick="zoomOut()">−</button>
        <button onclick="resetZoom()">⟳</button>
      </div>

      <div id="graph" class="mermaid" style="transform-origin: 0 0; width: 180%;">
      {mermaid}
      </div>
    </div>

    <style>
      .mermaid svg {{
        font-family: 'Inter', 'Segoe UI', sans-serif !important;
        font-size: 20px !important;
        font-weight: 600 !important;
      }}
      .mermaid svg foreignObject div {{
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        white-space: normal !important;
        word-wrap: break-word;
        width: auto !important;
        min-width: 220px;
        max-width: 420px;
        min-height: 80px;
        padding: 12px 16px;
        line-height: 1.3;
      }}
      .mermaid svg rect, .mermaid svg ellipse {{
        rx: 16px; ry: 16px;
        filter: drop-shadow(1px 1px 3px rgba(0,0,0,0.15));
      }}
      .mermaid svg text {{
        fill: #000 !important;
      }}
      #zoom-controls button {{
        border: 1px solid #ccc;
        border-radius: 4px;
        background: #f9f9f9;
        cursor: pointer;
        margin-left: 4px;
      }}
      #zoom-controls button:hover {{
        background: #e0e0e0;
      }}
    </style>

    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{
        startOnLoad: true,
        theme: "neutral",
        flowchart: {{
          curve: "basis",
          htmlLabels: true,
          useMaxWidth: false
        }}
      }});

      // Zoom & pan
      let scale = 1;
      const container = document.getElementById('graph-container');
      const graph = document.getElementById('graph');

      container.addEventListener('wheel', e => {{
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        scale = Math.min(Math.max(0.4, scale + delta), 3);
        graph.style.transform = `scale(${{scale}})`;
      }});

      function zoomIn() {{ scale = Math.min(scale + 0.25, 3); graph.style.transform = `scale(${{scale}})`; }}
      function zoomOut() {{ scale = Math.max(scale - 0.25, 0.4); graph.style.transform = `scale(${{scale}})`; }}
      function resetZoom() {{ scale = 1; graph.style.transform = "scale(1)"; }}

      window.zoomIn = zoomIn;
      window.zoomOut = zoomOut;
      window.resetZoom = resetZoom;

      let isDragging = false, startX, startY, offsetX=0, offsetY=0;
      container.addEventListener('mousedown', e => {{
        isDragging = true;
        startX = e.clientX - offsetX;
        startY = e.clientY - offsetY;
      }});
      container.addEventListener('mouseup', () => isDragging = false);
      container.addEventListener('mouseleave', () => isDragging = false);
      container.addEventListener('mousemove', e => {{
        if(!isDragging) return;
        offsetX = e.clientX - startX;
        offsetY = e.clientY - startY;
        graph.style.transform = `translate(${{offsetX}}px, ${{offsetY}}px) scale(${{scale}})`;
      }});
    </script>
    """
    return html


# ==============================
# VISUALIZACIÓN: ORGANIGRAMA (MERMAID)
# ==============================
def draw_org_mermaid(nodes):
    if not nodes:
        return None

    # Si no hay jerarquía clara, añadimos un root
    has_parents = any(n.get("parent") for n in nodes)
    if not has_parents:
        root_name = "Empresa Principal" if lang == "es" else "Main Company"
        root = {"name": root_name, "type": "group", "parent": None}
        for n in nodes:
            n["parent"] = root_name
        nodes.insert(0, root)

    mermaid = "flowchart TB\n"
    id_map = {}

    # crear nodos
    for i, n in enumerate(nodes):
        name = sanitize_label(n.get("name", f"Nodo {i+1}"))
        ntype = sanitize_label(n.get("type", ""))
        node_id = f"N{i}"
        id_map[name] = node_id
        label = name
        mermaid += f'  {node_id}["{label}"]\n'

        if "group" in ntype:
            mermaid += f"  class {node_id} groupNode;\n"
        elif "company" in ntype or "plant" in ntype:
            mermaid += f"  class {node_id} plantNode;\n"
        elif "department" in ntype:
            mermaid += f"  class {node_id} deptNode;\n"
        elif "team" in ntype:
            mermaid += f"  class {node_id} teamNode;\n"

    # relaciones
    for n in nodes:
        parent_name = n.get("parent")
        child_name = n.get("name")
        if parent_name and parent_name in id_map and child_name in id_map:
            mermaid += f"  {id_map[parent_name]} --> {id_map[child_name]}\n"

    mermaid += """
    classDef groupNode fill:#a7c7e7,stroke:#003366,stroke-width:2px,color:#000,font-size:20px,font-weight:bold;
    classDef plantNode fill:#b5e7a0,stroke:#2e7d32,stroke-width:2px,color:#000,font-size:18px;
    classDef deptNode fill:#fff3cd,stroke:#8c6d1f,stroke-width:2px,color:#000,font-size:18px;
    classDef teamNode fill:#e0e0e0,stroke:#616161,stroke-width:2px,color:#000,font-size:18px;
    """

    html = f"""
    <div class="mermaid" style="width:100%;height:800px;">
    {mermaid}
    </div>

    <style>
      .mermaid svg {{
        font-family: 'Inter', 'Segoe UI', sans-serif !important;
        font-size: 18px !important;
      }}
      .mermaid svg foreignObject div {{
        display:flex;
        align-items:center;
        justify-content:center;
        text-align:center;
        white-space:normal !important;
        word-wrap:break-word;
        width:auto !important;
        min-width:200px;
        max-width:420px;
        padding:10px 14px;
        line-height:1.3;
      }}
      .mermaid svg rect {{
        rx:12px; ry:12px;
        filter: drop-shadow(1px 1px 3px rgba(0,0,0,0.15));
      }}
    </style>

    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{
        startOnLoad: true,
        theme: "neutral",
        flowchart: {{
          htmlLabels: true,
          useMaxWidth: true
        }}
      }});
    </script>
    """
    return html


# ==============================
# ANÁLISIS CON IA
# ==============================
if analyze:
    if not text.strip():
        st.warning(TXT["warn_no_text"])
    else:
        with st.spinner(TXT["spinner"]):
            prep = preprocess_transcript(text)
            data = call_openai_json(unified_prompt(lang), prep["text"])
            # añadimos hablantes detectados como participantes (sin duplicar)
            detected = prep["speakers"]
            existing_participants = set(data.get("participants", []))
            for sp in detected:
                if sp not in existing_participants:
                    existing_participants.add(sp)
            data["participants"] = list(existing_participants)
            st.session_state.company_data = data

# ==============================
# RESULTADOS
# ==============================
if "company_data" in st.session_state:
    d = st.session_state.company_data

    org = d.get("organization", {})
    proc = d.get("process", {})
    participants = d.get("participants", [])

    steps = proc.get("steps", [])
    pains = proc.get("pains", [])
    recs = proc.get("recommendations", [])
    nodes = org.get("nodes", [])
    org_notes = org.get("notes", [])

    tabs = st.tabs(TXT["tabs"])

    # --- TAB 0: Mapa de Procesos ---
    with tabs[0]:
        html = draw_process_mermaid(steps)
        if html:
            components.html(html, height=950, scrolling=True)
        else:
            st.info(TXT["no_data"])

    # --- TAB 1: Datos del Proceso ---
    with tabs[1]:
        st.subheader("JSON de proceso")
        st.json(proc)
        if steps:
            st.subheader("Tabla de pasos")
            st.dataframe(pd.DataFrame(steps))
        if pains:
            st.subheader("Pain points")
            st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))

    # --- TAB 2: Estructura Organizacional ---
    with tabs[2]:
        html_org = draw_org_mermaid(nodes)
        if html_org:
            components.html(html_org, height=850, scrolling=True)
        else:
            st.info(TXT["no_data"])

    # --- TAB 3: Datos Organizativos ---
    with tabs[3]:
        st.subheader("JSON de organización")
        st.json(org)
        if nodes:
            st.subheader("Nodos")
            st.dataframe(pd.DataFrame(nodes))
        if org_notes:
            st.subheader("Notas")
            st.write(org_notes)

    # --- TAB 4: Participantes ---
    with tabs[4]:
        if participants:
            st.dataframe(pd.DataFrame(participants, columns=["Participante"]))
        else:
            st.info("No se detectaron participantes.")

    # --- TAB 5: Recomendaciones IA ---
    with tabs[5]:
        if recs:
            st.dataframe(pd.DataFrame(recs))
        else:
            st.info(TXT["no_data"])

    # --- TAB 6: Exportar ---
    with tabs[6]:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(steps).to_excel(
                excel_writer=writer, sheet_name="Steps", index=False
            )
            pd.DataFrame(pains).to_excel(
                excel_writer=writer, sheet_name="Pains", index=False
            )
            pd.DataFrame(recs).to_excel(
                excel_writer=writer, sheet_name="Recs", index=False
            )
            pd.DataFrame(nodes).to_excel(
                excel_writer=writer, sheet_name="OrgNodes", index=False
            )
            pd.DataFrame(participants).to_excel(
                excel_writer=writer, sheet_name="Participants", index=False
            )
        buffer.seek(0)
        st.download_button(
            label=TXT["export_label"],
            data=buffer,
            file_name="company_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("👆 Introduce texto y pulsa en analizar para ver resultados.")
