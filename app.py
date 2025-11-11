import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import io
import re
import streamlit.components.v1 as components

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(page_title="AI Workshop Assistant PRO", layout="wide")

st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(2) {text-align:right;}
button[role="button"] {border-radius:12px!important;}
</style>
""", unsafe_allow_html=True)

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
            st.session_state.lang = "en"; st.rerun()
    else:
        if st.button("🇪🇸", help="Cambiar a Español"):
            st.session_state.lang = "es"; st.rerun()

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
        "intro": "Analyze workshop transcripts to automatically build **process and org structures**.",
        "input_label": "✏️ Paste transcript or description:",
        "input_ph": "Example: Matías: client places an order. Sofía: quality reviews the batch...",
        "analyze_btn": "🚀 Analyze company and processes",
        "spinner": "Analyzing with AI...",
        "warn_no_text": "Please enter text to analyze.",
        "tabs": [
            "🗺️ Process Map",
            "🏗️ Org Structure",
            "🧩 Process Data",
            "📋 Org Data",
            "👥 Participants",
            "💡 AI Recommendations",
            "📤 Export"
        ],
        "no_data": "No data detected.",
        "export_label": "⬇️ Download Excel"
    }
}[lang]

st.markdown(TXT["intro"])
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==============================
# INPUT
# ==============================
text = st.text_area(TXT["input_label"], placeholder=TXT["input_ph"], height=200)
analyze = st.button(TXT["analyze_btn"])

# ==============================
# HELPERS
# ==============================
def preprocess_transcript(t):
    speakers = re.findall(r"(\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+):", t)
    clean = re.sub(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+:\s*", "", t)
    return {"speakers": list(set(speakers)), "text": clean.strip()}

def unified_prompt(lang):
    if lang == "es":
        return """Eres un consultor experto en procesos. 
Extrae tres bloques JSON: participants, organization, process.
Devuelve SOLO un JSON válido:
{
 "participants":[{"name":"Matías","role":"Planner"}],
 "organization":{"nodes":[{"name":"Manufactura","type":"department","parent":null}],"notes":["Estructura básica."]},
 "process":{"steps":[{"name":"Inicio","actor":"Cliente","department":"Comercial","type":"start"},
 {"name":"Revisión","actor":"Sofía","department":"Calidad","type":"task"},
 {"name":"Producción","actor":"Carlos","department":"Producción","type":"task"},
 {"name":"¿Aprobado?","actor":"Lucía","department":"Calidad","type":"decision"},
 {"name":"Fin","actor":"Sistema","department":"TI","type":"end"}],
 "pains":["Retraso en revisión"],"recommendations":[{"area":"Calidad","recommendation":"Automatizar control"}]}
}"""
    else:
        return """You are a business process expert.
Extract three JSON blocks: participants, organization, process.
Return ONLY a valid JSON as:
{
 "participants":[{"name":"Matías","role":"Planner"}],
 "organization":{"nodes":[{"name":"Manufacturing","type":"department","parent":null}],"notes":["Basic structure."]},
 "process":{"steps":[{"name":"Start","actor":"Client","department":"Sales","type":"start"},
 {"name":"Review","actor":"Sofía","department":"Quality","type":"task"},
 {"name":"Production","actor":"Carlos","department":"Manufacturing","type":"task"},
 {"name":"Approved?","actor":"Lucía","department":"Quality","type":"decision"},
 {"name":"End","actor":"System","department":"IT","type":"end"}],
 "pains":["Delay in review"],"recommendations":[{"area":"Quality","recommendation":"Automate QC"}]}
}"""

def call_openai_json(system_prompt, user_text):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_text[:4000]}],
            temperature=0.3,max_tokens=1000)
        c = r.choices[0].message.content.strip()
        j = re.search(r"\{.*\}", c, re.S)
        return json.loads(j.group(0)) if j else {}
    except Exception as e:
        st.error(f"Error con OpenAI: {e}")
        return {}

# ==============================
# VISUALIZACIÓN
# ==============================
def sanitize_label(text):
    return re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ,.!?¿¡:/()_-]', '', text or '').replace("\n", " ")

# --- NUEVO Mapa de Procesos con swimlanes reales ---
def draw_process_mermaid(steps):
    if not steps:
        return None

    # === Detectar departamentos únicos (lanes horizontales) ===
    departments = []
    for s in steps:
        d = s.get("department") or s.get("actor") or "General"
        if d not in departments:
            departments.append(d)

    node_map = {}
    mermaid = "flowchart LR\n"

    # === Crear un lane por departamento, todos a igual altura ===
    for dept in departments:
        mermaid += f"  subgraph {sanitize_label(dept)}\n"
        for i, s in enumerate([x for x in steps if (x.get('department') or x.get('actor') or 'General') == dept]):
            idx = steps.index(s)
            name = sanitize_label(s.get("name", f"Paso {idx+1}"))
            actor = sanitize_label(s.get("actor", ""))
            label = f"{name}\\n({actor})" if actor else name
            node_type = s.get("type", "task")

            if node_type == "start":
                node = f'N{idx}((\"{label}\")):::startNode'
            elif node_type == "end":
                node = f'N{idx}((\"{label}\")):::endNode'
            elif node_type == "decision":
                node = f'N{idx}{{\"{label}\"}}:::decisionNode'
            else:
                node = f'N{idx}[\"{label}\"]:::taskNode'
            node_map[idx] = dept
            mermaid += f"    {node}\n"
        mermaid += "  end\n\n"

    # === Conexiones izquierda→derecha ===
    mermaid += "%% --- Flujo ---\n"
    for i in range(len(steps) - 1):
        if node_map[i] != node_map[i + 1]:
            mermaid += f"  N{i} -.-> N{i+1}\n"   # cruzar lanes
        else:
            mermaid += f"  N{i} --> N{i+1}\n"

    # === Estilos visuales ===
    mermaid += """
    classDef startNode fill:#C8E6C9,stroke:#2E7D32,stroke-width:2px,color:#000,font-size:14px,font-weight:bold;
    classDef endNode fill:#FFCDD2,stroke:#B71C1C,stroke-width:2px,color:#000,font-size:14px,font-weight:bold;
    classDef decisionNode fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000,font-size:14px;
    classDef taskNode fill:#E3F2FD,stroke:#1565C0,stroke-width:1px,color:#000,font-size:14px;

    %% Lanes
    linkStyle default stroke-width:2px;
    """

    # === HTML contenedor con zoom/pan ===
    html = f"""
    <div id="graph-container" style="position:relative;width:100%;height:800px;overflow:hidden;border:1px solid #ddd;">
      <div id="zoom-controls" style="
          position:absolute;top:10px;right:10px;z-index:20;
          background:rgba(255,255,255,0.9);padding:5px 8px;border-radius:6px;
          box-shadow:0 1px 3px rgba(0,0,0,0.3);font-size:18px;">
        🔍 <button onclick="zoomIn()">+</button>
        <button onclick="zoomOut()">−</button>
        <button onclick="resetZoom()">⟳</button>
      </div>

      <div id="graph" class="mermaid" style="transform-origin: 0 0;">
      {mermaid}
      </div>
    </div>

    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{
        startOnLoad: true,
        theme: "neutral",
        flowchart: {{
          curve: "basis",
          htmlLabels: true
        }}
      }});

      // === Zoom & Pan ===
      let scale = 1;
      const container = document.getElementById('graph-container');
      const graph = document.getElementById('graph');
      container.addEventListener('wheel', e => {{
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        scale = Math.min(Math.max(0.3, scale + delta), 2.5);
        graph.style.transform = `scale(${{scale}})`;
      }});
      function zoomIn() {{ scale = Math.min(scale + 0.2, 3); graph.style.transform = `scale(${{scale}})`; }}
      function zoomOut() {{ scale = Math.max(scale - 0.2, 0.3); graph.style.transform = `scale(${{scale}})`; }}
      function resetZoom() {{ scale = 1; graph.style.transform = `scale(1)`; }}
      window.zoomIn = zoomIn; window.zoomOut = zoomOut; window.resetZoom = resetZoom;

      // Arrastrar el gráfico
      let isDragging = false, startX, startY, offsetX=0, offsetY=0;
      container.addEventListener('mousedown', e => {{ isDragging = true; startX = e.clientX - offsetX; startY = e.clientY - offsetY; }});
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


# --- Estructura Organizacional ---
def draw_org_mermaid(nodes):
    if not nodes:
        return None

    has_parents = any(n.get("parent") for n in nodes)
    if not has_parents:
        root = {"name": "Empresa Principal", "type": "group", "parent": None}
        for n in nodes:
            n["parent"] = "Empresa Principal"
        nodes.insert(0, root)

    mermaid = "graph TB\n"
    id_map = {}

    for i, n in enumerate(nodes):
        name = sanitize_label(n.get("name", "Nodo"))
        ntype = sanitize_label(n.get("type", ""))
        node_id = f"N{i}"
        id_map[name] = node_id
        label = f"{name}\\n({ntype})" if ntype else name
        mermaid += f'    {node_id}["{label}"]\n'
        if "group" in ntype:
            mermaid += f"    class {node_id} groupNode;\n"
        elif "company" in ntype or "plant" in ntype:
            mermaid += f"    class {node_id} plantNode;\n"
        elif "department" in ntype:
            mermaid += f"    class {node_id} deptNode;\n"
        elif "team" in ntype:
            mermaid += f"    class {node_id} teamNode;\n"

    for n in nodes:
        parent = sanitize_label(n.get("parent", ""))
        child = sanitize_label(n.get("name", ""))
        if parent and parent in id_map and child in id_map:
            mermaid += f'    {id_map[parent]} --> {id_map[child]}\n'

    mermaid += """
    classDef groupNode fill:#a7c7e7,stroke:#003366,stroke-width:1px,color:#000,font-weight:bold;
    classDef plantNode fill:#b5e7a0,stroke:#2e7d32,stroke-width:1px,color:#000;
    classDef deptNode fill:#fff3cd,stroke:#8c6d1f,stroke-width:1px,color:#000;
    classDef teamNode fill:#e0e0e0,stroke:#616161,stroke-width:1px,color:#000;
    """

    html = f"""
    <div class="mermaid">
    {mermaid}
    </div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true, theme: "neutral" }});
    </script>
    """
    return html

# ==============================
# ANÁLISIS
# ==============================
if "analyze" not in locals(): analyze=False
if analyze:
    if not text.strip():
        st.warning(TXT["warn_no_text"])
    else:
        with st.spinner(TXT["spinner"]):
            prep = preprocess_transcript(text)
            data = call_openai_json(unified_prompt(lang), prep["text"])
            data["participants"] = data.get("participants", []) + [{"name":p,"role":"Por inferir"} for p in prep["speakers"]]
            st.session_state.data = data

# ==============================
# RESULTADOS
# ==============================
if "data" in st.session_state:
    d = st.session_state.data
    org, proc, parts = d.get("organization",{}), d.get("process",{}), d.get("participants",[])
    steps = proc.get("steps",[]); pains = proc.get("pains",[]); recs = proc.get("recommendations",[]); nodes = org.get("nodes",[])

    tabs = st.tabs(TXT["tabs"])

    with tabs[0]:
        html = draw_process_mermaid(steps)
        if html: components.html(html, height=800, scrolling=True)
        else: st.info(TXT["no_data"])

    with tabs[1]:
        html = draw_org_mermaid(nodes)
        if html: components.html(html, height=800, scrolling=True)
        else: st.info(TXT["no_data"])

    with tabs[2]:
        if steps: st.dataframe(pd.DataFrame(steps))
        if pains: st.dataframe(pd.DataFrame(pains,columns=["Pain Points"]))

    with tabs[3]:
        if nodes: st.dataframe(pd.DataFrame(nodes))

    with tabs[4]:
        if parts: st.dataframe(pd.DataFrame(parts))
        else: st.info("No se detectaron hablantes.")

    with tabs[5]:
        if recs: st.dataframe(pd.DataFrame(recs))
        else: st.info(TXT["no_data"])

    with tabs[6]:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            pd.DataFrame(steps).to_excel(excel_writer=w, sheet_name="Steps", index=False)
            pd.DataFrame(pains).to_excel(excel_writer=w, sheet_name="Pains", index=False)
            pd.DataFrame(recs).to_excel(excel_writer=w, sheet_name="Recs", index=False)
            pd.DataFrame(nodes).to_excel(excel_writer=w, sheet_name="OrgNodes", index=False)
            pd.DataFrame(parts).to_excel(excel_writer=w, sheet_name="Participants", index=False)
        buf.seek(0)
        st.download_button(
            label=TXT["export_label"],
            data=buf,
            file_name="company_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
