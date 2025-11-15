import streamlit as st
import pandas as pd

# =============== STYLES ===============
st.set_page_config(page_title="AI Process Mapper", layout="wide")
st.markdown(
    """
    <style>
    .main {
        background-color: #fafafa;
        font-family: 'Inter', sans-serif;
    }
    button[title="View fullscreen"]{visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# =============== UTILIDAD ===============
def sanitize_label(label: str) -> str:
    return label.replace('"', '').replace("'", "").replace("\n", " ").strip()

# =============== DIAGRAMA DE PROCESOS ===============
def draw_process_mermaid(steps):
    if not steps:
        return None

    departments = []
    for s in steps:
        d = s.get("department") or "General"
        if d not in departments:
            departments.append(d)

    node_map = {}
    mermaid = "flowchart LR\n"

    # Crear lanes
    for dept in departments:
        mermaid += f"  subgraph {sanitize_label(dept)}\n"
        for i, s in enumerate([x for x in steps if (x.get('department') or 'General') == dept]):
            idx = steps.index(s)
            name = sanitize_label(s.get("name", f"Paso {idx+1}"))
            node_type = s.get("type", "task")

            if node_type == "start":
                node = f'N{idx}(["{name}"]):::startNode'
            elif node_type == "end":
                node = f'N{idx}(["{name}"]):::endNode'
            elif node_type == "decision":
                node = f'N{idx}{{"{name}"}}:::decisionNode'
            else:
                node = f'N{idx}["{name}"]:::taskNode'
            node_map[idx] = dept
            mermaid += f"    {node}\n"
        mermaid += "  end\n\n"

    # Conexiones
    for i in range(len(steps) - 1):
        if node_map[i] != node_map[i + 1]:
            mermaid += f"  N{i} -.-> N{i+1}\n"
        else:
            mermaid += f"  N{i} --> N{i+1}\n"

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
          background:rgba(255,255,255,0.9);padding:5px 8px;border-radius:6px;
          box-shadow:0 1px 3px rgba(0,0,0,0.3);font-size:22px;">
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
        font-family: 'Inter', sans-serif !important;
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
        max-width: 400px;
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
    </script>
    """
    return html


# =============== ORGANIGRAMA ===============
def draw_structure_mermaid(nodes):
    if not nodes:
        return None

    mermaid = "flowchart TB\n"
    for i, n in enumerate(nodes):
        name = sanitize_label(n.get("name", f"Elemento {i+1}"))
        ntype = n.get("type", "department")
        parent = n.get("parent")
        color = "#FFF"

        if ntype == "group":
            color = "#BBDEFB"
        elif ntype == "department":
            color = "#FFF9C4"
        elif ntype == "team":
            color = "#E1BEE7"

        mermaid += f'N{i}["{name}"]:::nodeStyle{i}\n'
        mermaid += f'classDef nodeStyle{i} fill:{color},stroke:#424242,stroke-width:2px,font-size:20px,font-weight:bold;\n'
        if parent is not None:
            mermaid += f"N{parent} --> N{i}\n"

    html = f"""
    <div id="structure" class="mermaid" style="width:100%;height:800px;">
    {mermaid}
    </div>
    <style>
      .mermaid svg {{
        font-family: 'Inter', sans-serif;
        font-size: 20px;
      }}
      .mermaid svg foreignObject div {{
        white-space: normal !important;
        word-wrap: break-word;
        width: auto !important;
        min-width: 200px;
        max-width: 400px;
        padding: 12px 14px;
        text-align: center;
      }}
    </style>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{
        startOnLoad: true,
        theme: "neutral",
        flowchart: {{
          useMaxWidth: false,
          htmlLabels: true
        }}
      }});
    </script>
    """
    return html


# =============== INTERFAZ STREAMLIT ===============
st.title("📊 AI Process & Structure Mapper")

tabs = st.tabs(["🗺️ Mapa de Procesos", "🏗️ Estructura Organizacional"])

with tabs[0]:
    st.subheader("Diagrama de Proceso")
    process_steps = [
        {"name": "Registro de orden de compra y validación de cliente", "department": "Ventas"},
        {"name": "Envío a Producción con instrucciones técnicas detalladas", "department": "Producción"},
        {"name": "Fabricación del producto según especificaciones del cliente", "department": "Producción"},
        {"name": "Control de inspección final del producto antes de envío", "department": "Calidad"},
        {"name": "Corrección de errores o retrabajo si no pasa inspección", "department": "Producción"},
        {"name": "Cierre de orden y notificación al cliente", "department": "Ventas", "type": "end"},
    ]
    html_chart = draw_process_mermaid(process_steps)
    st.components.v1.html(html_chart, height=950, scrolling=True)

with tabs[1]:
    st.subheader("Organigrama")
    structure_nodes = [
        {"name": "Empresa Principal", "type": "group"},
        {"name": "Producción", "type": "department", "parent": 0},
        {"name": "Calidad", "type": "department", "parent": 0},
        {"name": "Ventas", "type": "department", "parent": 0},
        {"name": "Logística y Distribución", "type": "team", "parent": 1},
        {"name": "Control de Procesos", "type": "team", "parent": 2},
    ]
    html_struct = draw_structure_mermaid(structure_nodes)
    st.components.v1.html(html_struct, height=850, scrolling=True)
