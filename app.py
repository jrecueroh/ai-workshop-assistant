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
 "process":{"steps":[{"name":"Inicio","actor":"Cliente","type":"start"},{"name":"Revisión","actor":"Calidad","type":"task"},{"name":"¿Aprobado?","actor":"Supervisor","type":"decision"},{"name":"Fin","actor":"Sistema","type":"end"}],
 "pains":["Retraso en revisión"],"recommendations":[{"area":"Calidad","recommendation":"Automatizar control"}]}
}"""
    else:
        return """You are a business process expert.
Extract three JSON blocks: participants, organization, process.
Return ONLY a valid JSON as:
{
 "participants":[{"name":"Matías","role":"Planner"}],
 "organization":{"nodes":[{"name":"Manufacturing","type":"department","parent":null}],"notes":["Basic structure."]},
 "process":{"steps":[{"name":"Start","actor":"Client","type":"start"},{"name":"Review","actor":"Quality","type":"task"},{"name":"Approved?","actor":"Supervisor","type":"decision"},{"name":"End","actor":"System","type":"end"}],
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
# VISUALIZACIÓN (MERMAID)
# ==============================
def sanitize_label(text):
    return re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ,.!?¿¡:/()_-]', '', text or '').replace("\n", " ")

def draw_process_mermaid(steps):
    if not steps:
        return None
    mermaid = "flowchart LR\n"
    for i, s in enumerate(steps):
        name = sanitize_label(s.get("name", f"Paso {i+1}"))
        actor = sanitize_label(s.get("actor", ""))
        label = f"{name}\\n({actor})" if actor else name
        node_type = s.get("type", "task")
        if node_type == "start":
            mermaid += f"    N{i}((\"{label}\"))\n"
        elif node_type == "end":
            mermaid += f"    N{i}((\"{label}\"))\n"
        elif node_type == "decision":
            mermaid += f"    N{i}{{\"{label}\"}}\n"
        else:
            mermaid += f"    N{i}[\"{label}\"]\n"
        if i < len(steps) - 1:
            mermaid += f"    N{i} --> N{i+1}\n"
    return f"""
    <div class="mermaid">
    {mermaid}
    </div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true, theme: "neutral" }});
    </script>
    """

def draw_org_mermaid(nodes):
    if not nodes:
        return None

    # Si no hay jerarquía, se crea una raíz
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

    return f"""
    <div class="mermaid">
    {mermaid}
    </div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true, theme: "neutral" }});
    </script>
    """

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
        if html: components.html(html, height=600, scrolling=True)
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
