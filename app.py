import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import re
import io
import streamlit.components.v1 as components

# ======================================================
# CONFIG GENERAL
# ======================================================
st.set_page_config(page_title="AI Workshop Assistant PRO", layout="wide")

st.markdown("""
<style>
button[role="button"] { border-radius: 10px!important; }
.main { font-family: 'Inter', sans-serif; }
button[title="View fullscreen"]{visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# IDIOMA
# ======================================================
if "lang" not in st.session_state:
    st.session_state.lang = "es"

col1, col2 = st.columns([6,1])
with col1: st.markdown("## 🧩 AI Workshop Assistant PRO")
with col2:
    if st.session_state.lang == "es":
        if st.button("🇬🇧"): st.session_state.lang = "en"; st.rerun()
    else:
        if st.button("🇪🇸"): st.session_state.lang = "es"; st.rerun()

lang = st.session_state.lang

# ======================================================
# TEXTOS
# ======================================================
TXT = {
    "es": {
        "intro": "Analiza transcripciones de workshops para generar **procesos, organización, participantes, KPIs y recomendaciones**.",
        "input_label": "✏️ Pega la transcripción del workshop:",
        "input_ph": "Ejemplo: Matías: El cliente hace un pedido...",
        "analyze_btn": "🚀 Analizar workshop",
        "spinner": "Analizando workshop...",
        "warn_no_text": "Introduce texto primero.",
        "tabs": [
            "🗺️ Mapa de Procesos",
            "🏗️ Estructura Organizacional",
            "📋 Datos Organizativos",
            "👥 Participantes",
            "📊 KPIs",
            "🔍 Root Causes",
            "🚦 Decisiones",
            "💡 Recomendaciones IA",
            "📤 Exportar"
        ],
        "no_data": "No se detectaron datos.",
        "export_label": "⬇️ Descargar Excel (PRO)"
    }
}[lang]

st.markdown(TXT["intro"])

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ======================================================
# HELPERS
# ======================================================
def preprocess_transcript(t):
    speakers = re.findall(r"(\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+):", t)
    clean = re.sub(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+:\s*", "", t)
    return {"speakers": sorted(list(set(speakers))), "text": clean.strip()}

def safe_json_extract(content):
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return content[start:end+1]

def unified_prompt(lang):
    return """
Eres un CONSULTOR experto en procesos, transformación empresarial, análisis de workshops y diseño organizativo.

⚠️ REGLAS:
- SOLO puedes responder con JSON válido.
- SIN explicaciones.
- SIN texto fuera del JSON.
- SIN ```json.
- Valida tu JSON antes de enviarlo.
- NO dejes comas colgando.
- Si falta información, infiérela.

ESTRUCTURA OBLIGATORIA:

{
  "organization": {
    "nodes": [{
      "name": "",
      "type": "group | company | plant | department | team",
      "parent": "",
      "responsibilities": [],
      "participants": []
    }],
    "hierarchy": [{"level": "", "elements": []}],
    "notes": []
  },

  "participants": [{
    "name": "",
    "role": "",
    "department": "",
    "responsibilities": [],
    "mentions": 0,
    "pain_points": [],
    "influence": "alta | media | baja"
  }],

  "process": {
    "steps": [{
      "name": "",
      "description": "",
      "department": "",
      "type": "start | task | decision | end",
      "inputs": [],
      "outputs": [],
      "systems": [],
      "pain_points": []
    }],
    "pains": [{
      "pain": "",
      "severity": "alta | media | baja",
      "root_cause": "",
      "impacted_roles": [],
      "estimated_cost": ""
    }],
    "recommendations": [{
      "area": "",
      "recommendation": "",
      "impact": "alto | medio | bajo",
      "effort": "alto | medio | bajo",
      "estimated_roi": ""
    }],
    "kpis": [{
      "name": "",
      "current": "",
      "target": "",
      "unit": ""
    }],
    "decisions": [{
      "topic": "",
      "decision": "",
      "owner": ""
    }]
  }
}

ANTES DE RESPONDER:
- Comprueba que tu JSON es válido.
- No olvides ningún campo obligatorio.
"""

def call_openai_json(system_prompt, user_text):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text[:6000]}
            ],
            temperature=0.15,
            max_tokens=1800
        )
        output = r.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error OpenAI: {e}")
        return {}

    json_str = safe_json_extract(output)
    if not json_str:
        st.error("⚠️ No se detectó JSON.")
        return {}

    try:
        return json.loads(json_str)
    except:
        st.error("⚠️ JSON inválido.")
        return {}
# ======================================================
# SANITIZER TEXTO
# ======================================================
def sanitize_label(t):
    if not t: return ""
    return str(t).replace('"', "").replace("'", "").replace("\n", " ").strip()

# ======================================================
# MERMAID — MAPA DE PROCESO PRO (WRAP REAL)
# ======================================================
def draw_process_mermaid(process):
    steps = process.get("steps", [])
    if not steps:
        return None

    departments = []
    for s in steps:
        d = s.get("department") or "General"
        if d not in departments:
            departments.append(d)

    mermaid = "flowchart LR\n"
    node_dept = {}

    # lanes por departamento
    for dept in departments:
        mermaid += f"  subgraph {sanitize_label(dept)}\n"
        dept_steps = [s for s in steps if (s.get("department") or "General") == dept]
        for s in dept_steps:
            idx = steps.index(s)
            name = sanitize_label(s.get("name"))
            stype = s.get("type","task")

            if stype=="start":
                node = f'N{idx}(["{name}"]):::startNode'
            elif stype=="end":
                node = f'N{idx}(["{name}"]):::endNode'
            elif stype=="decision":
                node = f'N{idx}{{"{name}"}}:::decisionNode'
            else:
                node = f'N{idx}["{name}"]:::taskNode'

            mermaid += "    " + node + "\n"
            node_dept[idx]=dept
        mermaid += "  end\n\n"

    # conexiones
    for i in range(len(steps)-1):
        if node_dept[i] != node_dept[i+1]:
            mermaid += f"  N{i} -.-> N{i+1}\n"
        else:
            mermaid += f"  N{i} --> N{i+1}\n"

    # estilos
    mermaid += """
classDef startNode fill:#C8E6C9,stroke:#2E7D32,stroke-width:3px,color:#000,font-size:18px,font-weight:bold;
classDef endNode fill:#FFCDD2,stroke:#B71C1C,stroke-width:3px,color:#000,font-size:18px,font-weight:bold;
classDef decisionNode fill:#FFF9C4,stroke:#F57F17,stroke-width:3px,color:#000,font-size:18px,font-weight:bold;
classDef taskNode fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#000,font-size:18px,font-weight:bold;
linkStyle default stroke-width:2px;
"""

    # HTML con WRAP, ZOOM, PAN
    html = f"""
<div id="proc-container" style="position:relative;width:100%;height:900px;overflow:hidden;border:1px solid #ddd;">
<div id="proc-graph" class="mermaid" style="transform-origin:0 0; width:180%;">
{mermaid}
</div>
</div>

<style>
.mermaid svg {{
  font-family:'Inter',sans-serif !important;
  font-size:18px !important;
}}
.mermaid svg foreignObject div {{
  white-space:normal !important;
  word-wrap:break-word;
  word-break:break-word;
  padding:10px;
  width:auto !important;
  min-width:220px;
  max-width:420px;
  line-height:1.3;
}}
</style>

<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
mermaid.initialize({{ startOnLoad:true, flowchart:{{htmlLabels:true,useMaxWidth:false}} }});

let scale=1;
const container=document.getElementById("proc-container");
const graph=document.getElementById("proc-graph");

container.addEventListener("wheel",(e)=>{
  e.preventDefault();
  scale += (e.deltaY>0? -0.1:0.1);
  scale=Math.min(Math.max(0.4,scale),3);
  graph.style.transform=`scale(${scale})`;
});

let drag=false, sx, sy, ox=0, oy=0;
container.addEventListener("mousedown",(e)=>{{drag=true; sx=e.clientX-ox; sy=e.clientY-oy;}});
container.addEventListener("mouseup",()=>drag=false);
container.addEventListener("mouseleave",()=>drag=false);
container.addEventListener("mousemove",(e)=>{
  if(!drag) return;
  ox=e.clientX-sx; oy=e.clientY-sy;
  graph.style.transform=`translate(${ox}px,${oy}px) scale(${scale})`;
});
</script>
"""
    return html

# ======================================================
# MERMAID — ORGANIGRAMA PRO
# ======================================================
def draw_org_mermaid(org):
    nodes = org.get("nodes", [])
    if not nodes:
        return None

    # root si no existe
    if not any(n.get("parent") is None for n in nodes):
        root = {
            "name":"Empresa",
            "type":"group",
            "parent":None,
            "responsibilities":[],
            "participants":[]
        }
        for n in nodes: n["parent"]="Empresa"
        nodes.insert(0,root)

    mermaid="flowchart TB\n"
    idmap={}

    for i,n in enumerate(nodes):
        name=sanitize_label(n.get("name"))
        nid=f"N{i}"
        idmap[name]=nid
        mermaid+=f'  {nid}["{name}"]\n'
        t=n.get("type","")
        if "group" in t: mermaid+=f"  class {nid} groupNode;\n"
        elif "department" in t: mermaid+=f"  class {nid} deptNode;\n"
        elif "team" in t: mermaid+=f"  class {nid} teamNode;\n"

    for n in nodes:
        p=n.get("parent")
        c=n.get("name")
        if p and p in idmap and c in idmap:
            mermaid+=f"  {idmap[p]} --> {idmap[c]}\n"

    mermaid += """
classDef groupNode fill:#A7C7E7,stroke:#003366,stroke-width:2px,color:#000,font-size:18px,font-weight:bold;
classDef deptNode fill:#FFF3CD,stroke:#8C6D1F,stroke-width:2px,color:#000,font-size:16px;
classDef teamNode fill:#E0E0E0,stroke:#616161,stroke-width:2px,color:#000,font-size:16px;
"""

    html=f"""
<div class="mermaid" style="width:100%;height:800px;">
{mermaid}
</div>

<style>
.mermaid svg {{
  font-family:'Inter',sans-serif !important;
  font-size:16px!important;
}}
.mermaid svg foreignObject div {{
  white-space:normal!important;
  word-wrap:break-word;
  word-break:break-word;
  padding:10px;
  min-width:180px;
  max-width:420px;
}}
</style>

<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
mermaid.initialize({{ startOnLoad:true, flowchart:{{htmlLabels:true,useMaxWidth:true}} }});
</script>
"""
    return html
# ======================================================
# INPUT
# ======================================================
text = st.text_area(
    TXT["input_label"], placeholder=TXT["input_ph"], height=240
)
analyze = st.button(TXT["analyze_btn"])

# ======================================================
# ANALIZAR
# ======================================================
if analyze:
    if not text.strip():
        st.warning(TXT["warn_no_text"])
    else:
        with st.spinner(TXT["spinner"]):
            prep = preprocess_transcript(text)
            data = call_openai_json(unified_prompt(lang), prep["text"])

            # merge de speakers detectados
            speakers = prep["speakers"]
            participants = data.get("participants", [])
            existing = {p["name"] for p in participants if "name" in p}

            for sp in speakers:
                if sp not in existing:
                    participants.append({
                        "name": sp,
                        "role": "",
                        "department": "",
                        "responsibilities": [],
                        "mentions": 0,
                        "pain_points": [],
                        "influence": ""
                    })
            data["participants"] = participants

            st.session_state.company_data = data

# ======================================================
# RESULTADOS
# ======================================================
if "company_data" in st.session_state:
    d = st.session_state.company_data

    org = d.get("organization", {}) or {}
    proc = d.get("process", {}) or {}
    parts = d.get("participants", []) or []

    pains = proc.get("pains", []) or []
    kpis = proc.get("kpis", []) or []
    recs = proc.get("recommendations", []) or []
    decisions = proc.get("decisions", []) or []
    hierarchy = org.get("hierarchy", []) or []
    nodes = org.get("nodes", []) or []
    org_notes = org.get("notes", []) or []

    tabs = st.tabs(TXT["tabs"])

    # MAPA PROCESO
    with tabs[0]:
        html = draw_process_mermaid(proc)
        if html:
            components.html(html, height=950, scrolling=True)
        else:
            st.info(TXT["no_data"])

    # ORG CHART
    with tabs[1]:
        html = draw_org_mermaid(org)
        if html:
            components.html(html, height=850, scrolling=True)
        else:
            st.info(TXT["no_data"])

    # DATOS ORG
    with tabs[2]:
        st.subheader("Jerarquía")
        st.dataframe(pd.DataFrame(hierarchy))
        st.subheader("Notas")
        for n in org_notes:
            st.markdown(f"- {n}")

    # PARTICIPANTES
    with tabs[3]:
        dfp = pd.DataFrame(parts)
        st.dataframe(dfp)

    # KPIs
    with tabs[4]:
        if kpis:
            st.dataframe(pd.DataFrame(kpis))
        else:
            st.info(TXT["no_data"])

    # ROOT CAUSES
    with tabs[5]:
        if pains:
            st.dataframe(pd.DataFrame(pains))
        else:
            st.info(TXT["no_data"])

    # DECISIONES
    with tabs[6]:
        if decisions:
            st.dataframe(pd.DataFrame(decisions))
        else:
            st.info(TXT["no_data"])

    # RECOMENDACIONES
    with tabs[7]:
        if recs:
            st.dataframe(pd.DataFrame(recs))
        else:
            st.info(TXT["no_data"])

    # EXPORTAR
    with tabs[8]:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as w:
            pd.DataFrame(proc.get("steps",[])).to_excel(excel_writer=w, sheet_name="Steps", index=False)
            pd.DataFrame(pains).to_excel(excel_writer=w, sheet_name="Pains", index=False)
            pd.DataFrame(recs).to_excel(excel_writer=w, sheet_name="Recommendations", index=False)
            pd.DataFrame(kpis).to_excel(excel_writer=w, sheet_name="KPIs", index=False)
            pd.DataFrame(decisions).to_excel(excel_writer=w, sheet_name="Decisions", index=False)
            pd.DataFrame(nodes).to_excel(excel_writer=w, sheet_name="OrgNodes", index=False)
            pd.DataFrame(hierarchy).to_excel(excel_writer=w, sheet_name="OrgHierarchy", index=False)
            pd.DataFrame(parts).to_excel(excel_writer=w, sheet_name="Participants", index=False)

        buffer.seek(0)
        st.download_button(
            TXT["export_label"],
            buffer,
            "workshop_analysis_pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
