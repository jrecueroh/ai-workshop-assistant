import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import re
import io
import streamlit.components.v1 as components

# =====================================
# CONFIGURACIÓN GENERAL
# =====================================
st.set_page_config(page_title="AI Workshop Assistant PRO", layout="wide")

st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {text-align:right;}
    button[role="button"] {border-radius:12px!important;}
    .main {font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;}
    button[title="View fullscreen"]{visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================
# IDIOMA
# =====================================
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

# =====================================
# TEXTOS
# =====================================
TXT = {
    "es": {
        "intro": "Analiza descripciones o transcripciones de workshops para generar **procesos, estructura organizativa, participantes, KPIs y recomendaciones** automáticamente.",
        "input_label": "✏️ Pega aquí la transcripción o descripción del workshop:",
        "input_ph": "Ejemplo: Matías: el cliente hace un pedido. Sofía: se revisa la orden...",
        "analyze_btn": "🚀 Analizar workshop",
        "spinner": "Analizando con IA...",
        "warn_no_text": "Por favor introduce texto para analizar.",
        # OJO: ya NO hay 'Datos del proceso'
        "tabs": [
            "🗺️ Mapa de Procesos",
            "🏗️ Estructura Organizacional",
            "📋 Datos Organizativos",
            "👥 Participantes",
            "📊 KPIs",
            "🔍 Root Causes",
            "🚦 Decisiones",
            "💡 Recomendaciones IA",
            "📤 Exportar",
        ],
        "no_data": "No se detectaron datos.",
        "export_label": "⬇️ Descargar Excel con toda la información PRO",
    },
    "en": {
        "intro": "Analyze workshop transcripts to automatically generate **processes, org structure, participants, KPIs and AI recommendations**.",
        "input_label": "✏️ Paste the workshop transcript or description:",
        "input_ph": "Example: Matías: the client places an order. Sofía: quality reviews it...",
        "analyze_btn": "🚀 Analyze workshop",
        "spinner": "Analyzing with AI...",
        "warn_no_text": "Please enter text to analyze.",
        "tabs": [
            "🗺️ Process Map",
            "🏗️ Org Structure",
            "📋 Org Data",
            "👥 Participants",
            "📊 KPIs",
            "🔍 Root Causes",
            "🚦 Decisions",
            "💡 AI Recommendations",
            "📤 Export",
        ],
        "no_data": "No data detected.",
        "export_label": "⬇️ Download Excel (full PRO data)",
    },
}[lang]

st.markdown(TXT["intro"])

# =====================================
# CLIENTE OPENAI
# =====================================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =====================================
# INPUT
# =====================================
text = st.text_area(
    TXT["input_label"], placeholder=TXT["input_ph"], height=220, key="main_text"
)
analyze = st.button(TXT["analyze_btn"])


# =====================================
# HELPERS
# =====================================
def preprocess_transcript(t: str):
    """
    Detecta patrones tipo 'Nombre:' al inicio de frase.
    Devuelve:
    - lista de nombres únicos
    - texto sin los 'Nombre:'
    """
    speakers = re.findall(r"(\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+):", t)
    clean = re.sub(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+:\s*", "", t)
    return {"speakers": sorted(list(set(speakers))), "text": clean.strip()}


def unified_prompt(current_lang: str) -> str:
    # Prompt PRO: fuerza estructura rica, KPIs, pains, etc.
    return """
Eres un CONSULTOR EXPERTO en:
- Procesos de negocio (BPMN, Lean, Six Sigma)
- Diseño organizativo
- Transformación financiera y operacional
- Análisis de workshops y reuniones

Analiza el siguiente WORKSHOP (con personas hablando, problemas, ideas, procesos) y devuelve SOLO un JSON **PROFESIONAL**, con esta estructura EXACTA:

{
  "organization": {
    "nodes": [
      {
        "name": "",
        "type": "group | company | plant | department | team",
        "parent": "",
        "responsibilities": [],
        "participants": []
      }
    ],
    "hierarchy": [
      {"level": "", "elements": []}
    ],
    "notes": []
  },

  "participants": [
    {
      "name": "",
      "role": "",
      "department": "",
      "responsibilities": [],
      "mentions": 0,
      "pain_points": [],
      "influence": "alta | media | baja"
    }
  ],

  "process": {
    "steps": [
      {
        "name": "",
        "description": "",
        "department": "",
        "type": "start | task | decision | end",
        "inputs": [],
        "outputs": [],
        "systems": [],
        "pain_points": []
      }
    ],
    "pains": [
      {
        "pain": "",
        "severity": "alta | media | baja",
        "root_cause": "",
        "impacted_roles": [],
        "estimated_cost": ""
      }
    ],
    "recommendations": [
      {
        "area": "",
        "recommendation": "",
        "impact": "alto | medio | bajo",
        "effort": "alto | medio | bajo",
        "estimated_roi": ""
      }
    ],
    "kpis": [
      {"name": "", "current": "", "target": "", "unit": ""}
    ],
    "decisions": [
      {"topic": "", "decision": "", "owner": ""}
    ]
  }
}

REGLAS IMPORTANTES:
- NO incluyas explicaciones fuera del JSON.
- NO envuelvas el JSON en ``` ni en texto adicional.
- NO inventes nombres de personas que no aparezcan en el workshop.
- SI puedes inferir roles (ej. 'Director Financiero', 'Analista', etc.), hazlo.
- Usa el nombre de la empresa si aparece (ej: 'Grupo Financiero', 'Empresa X') como nodo raíz (type 'group' o 'company', parent null).
- Los nombres de personas van SOLO en "participants".
- Las descripciones de procesos NO deben tener nombres de personas, solo departamentos o funciones.
- La estructura organizacional debe agrupar empresa/grupo, departamentos y equipos, con responsabilidades.
- Genera SIEMPRE al menos 3 pains con root_cause y estimated_cost, si hay suficiente información.
- Genera SIEMPRE al menos 3 recomendaciones relevantes, con impacto y esfuerzo.
- Genera SIEMPRE al menos 3 KPIs relevantes al contexto, aunque no se mencionen explícitos (por ejemplo, en Finanzas: DSO, tiempo medio de facturación, etc.).
- Incluye decisiones explícitas e implícitas que el equipo debe tomar.
- Evita listas vacías si hay información suficiente en el texto.
"""


def call_openai_json(system_prompt: str, user_text: str):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                    + "\n\n⚠️ Devuelve solo JSON válido, sin explicaciones.",
                },
                {"role": "user", "content": user_text[:6000]},
            ],
            temperature=0.25,
            max_tokens=1500,
            timeout=60,
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
        str(text)
        .replace('"', "")
        .replace("'", "")
        .replace("\n", " ")
        .strip()
    )


# =====================================
# VISUALIZACIÓN: MAPA DE PROCESOS (MERMAID)
# =====================================
def draw_process_mermaid(process_dict: dict):
    steps = process_dict.get("steps", []) if process_dict else []
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
        dept_steps = [x for x in steps if (x.get("department") or "General") == dept]
        for s in dept_steps:
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
        word-break: break-word;
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


# =====================================
# VISUALIZACIÓN: ORGANIGRAMA (MERMAID)
# =====================================
def draw_org_mermaid(org_dict: dict):
    nodes = org_dict.get("nodes", []) if org_dict else []
    if not nodes:
        return None

    # Si no hay jerarquía clara, añadimos un root genérico
    has_parents = any(n.get("parent") for n in nodes)
    if not has_parents:
        root_name = "Grupo Financiero" if any("financ" in (n.get("name","").lower()) for n in nodes) else (
            "Empresa" if lang == "es" else "Company"
        )
        root = {
            "name": root_name,
            "type": "group",
            "parent": None,
            "responsibilities": [],
            "participants": [],
        }
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

        if "group" in ntype or "company" in ntype:
            mermaid += f"  class {node_id} groupNode;\n"
        elif "plant" in ntype:
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
        word-break:break-word;
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


# =====================================
# ANÁLISIS CON IA
# =====================================
if analyze:
    if not text.strip():
        st.warning(TXT["warn_no_text"])
    else:
        with st.spinner(TXT["spinner"]):
            prep = preprocess_transcript(text)
            data = call_openai_json(unified_prompt(lang), prep["text"])

            # mergeamos nombres detectados como participantes extra (si no estaban)
            speakers = prep["speakers"]
            participants = data.get("participants", [])
            existing_names = {
                p.get("name") for p in participants if isinstance(p, dict)
            }
            for sp in speakers:
                if sp not in existing_names:
                    participants.append(
                        {
                            "name": sp,
                            "role": "",
                            "department": "",
                            "responsibilities": [],
                            "mentions": 0,
                            "pain_points": [],
                            "influence": "",
                        }
                    )
            data["participants"] = participants

            st.session_state.company_data = data

# =====================================
# RESULTADOS
# =====================================
if "company_data" in st.session_state:
    d = st.session_state.company_data

    org = d.get("organization", {}) or {}
    proc = d.get("process", {}) or {}
    participants = d.get("participants", []) or []

    steps = proc.get("steps", []) or []
    pains = proc.get("pains", []) or []
    recs = proc.get("recommendations", []) or []
    kpis = proc.get("kpis", []) or []
    decisions = proc.get("decisions", []) or []

    nodes = org.get("nodes", []) or []
    hierarchy = org.get("hierarchy", []) or []
    org_notes = org.get("notes", []) or []

    tabs = st.tabs(TXT["tabs"])

    # --- TAB 0: Mapa de Procesos ---
    with tabs[0]:
        html = draw_process_mermaid(proc)
        if html:
            components.html(html, height=950, scrolling=True)
        else:
            st.info(TXT["no_data"])

    # --- TAB 1: Estructura Organizacional ---
    with tabs[1]:
        html_org = draw_org_mermaid(org)
        if html_org:
            components.html(html_org, height=850, scrolling=True)
        else:
            st.info(TXT["no_data"])

    # --- TAB 2: Datos Organizativos ---
    with tabs[2]:
        st.subheader("Estructura (JSON)")
        st.json(org)
        if nodes:
            st.subheader("Nodos organizativos")
            st.dataframe(pd.DataFrame(nodes))
        if hierarchy:
            st.subheader("Jerarquía")
            st.dataframe(pd.DataFrame(hierarchy))
        if org_notes:
            st.subheader("Notas / insights estructurales")
            for n in org_notes:
                st.markdown(f"- {n}")

    # --- TAB 3: Participantes (formato consultoría) ---
    with tabs[3]:
        if participants:
            st.subheader("Stakeholders del workshop")
            df_part = pd.DataFrame(participants)
            # orden de columnas si existen
            cols_order = [
                "name",
                "role",
                "department",
                "responsibilities",
                "pain_points",
                "mentions",
                "influence",
            ]
            existing_cols = [c for c in cols_order if c in df_part.columns]
            other_cols = [c for c in df_part.columns if c not in existing_cols]
            df_part = df_part[existing_cols + other_cols]
            st.dataframe(df_part)
        else:
            st.info("No se detectaron participantes.")

    # --- TAB 4: KPIs ---
    with tabs[4]:
        if kpis:
            st.subheader("KPIs identificados")
            st.dataframe(pd.DataFrame(kpis))
        else:
            st.info("No se detectaron KPIs explícitos o inferidos.")

    # --- TAB 5: Root Causes (pains) ---
    with tabs[5]:
        if pains:
            st.subheader("Root causes y pains")
            st.dataframe(pd.DataFrame(pains))
        else:
            st.info("No se detectaron pains o causas raíz.")

    # --- TAB 6: Decisiones ---
    with tabs[6]:
        if decisions:
            st.subheader("Decisiones y temas abiertos")
            st.dataframe(pd.DataFrame(decisions))
        else:
            st.info("No se detectaron decisiones claras en el workshop.")

    # --- TAB 7: Recomendaciones IA ---
    with tabs[7]:
        if recs:
            st.subheader("Recomendaciones priorizadas")
            df = pd.DataFrame(recs)
            st.dataframe(df)
        else:
            st.info("La IA no ha generado recomendaciones explícitas.")

    # --- TAB 8: Exportar ---
    with tabs[8]:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(steps).to_excel(
                excel_writer=writer, sheet_name="Steps", index=False
            )
            pd.DataFrame(pains).to_excel(
                excel_writer=writer, sheet_name="Pains", index=False
            )
            pd.DataFrame(recs).to_excel(
                excel_writer=writer, sheet_name="Recommendations", index=False
            )
            pd.DataFrame(kpis).to_excel(
                excel_writer=writer, sheet_name="KPIs", index=False
            )
            pd.DataFrame(decisions).to_excel(
                excel_writer=writer, sheet_name="Decisions", index=False
            )
            pd.DataFrame(nodes).to_excel(
                excel_writer=writer, sheet_name="OrgNodes", index=False
            )
            pd.DataFrame(hierarchy).to_excel(
                excel_writer=writer, sheet_name="OrgHierarchy", index=False
            )
            pd.DataFrame(participants).to_excel(
                excel_writer=writer, sheet_name="Participants", index=False
            )
        buffer.seek(0)
        st.download_button(
            label=TXT["export_label"],
            data=buffer,
            file_name="workshop_analysis_pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("👆 Pega una transcripción de workshop y pulsa en analizar para ver el asistente en acción.")
