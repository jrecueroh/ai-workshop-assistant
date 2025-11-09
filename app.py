import streamlit as st
from openai import OpenAI
import pandas as pd
from graphviz import Digraph
import json
import tempfile
import os

# ==========================================
# CONFIGURACIÓN BÁSICA
# ==========================================
st.set_page_config(page_title="AI Workshop Assistant — BPM Visualizer", layout="wide")
st.title("🧩 AI Workshop Assistant — Business Process Visualizer")

st.markdown("""
Convierte tu descripción de proceso o workshop en un **mapa visual estilo BPMN**,  
junto con una estructura organizada y stakeholders identificados automáticamente.
""")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==========================================
# ENTRADA
# ==========================================
input_text = st.text_area(
    "✏️ Pega la transcripción o descripción del proceso",
    height=250,
    placeholder="Ejemplo: El cliente hace un pedido, verificamos si hay stock disponible..."
)

if st.button("🚀 Analizar y generar mapa"):
    if not input_text.strip():
        st.warning("Por favor ingresa una descripción del proceso.")
        st.stop()

    with st.spinner("Analizando con IA..."):
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": """
Eres un experto en modelado de procesos empresariales (BPMN). 
Analiza la descripción y devuelve un JSON **simple** con la siguiente estructura:

{
 "steps": [
   {"name": "Customer places order", "type": "task", "actor": "Customer"},
   {"name": "Product available?", "type": "decision"},
   {"name": "Process Payment", "type": "task", "actor": "Sales"},
   {"name": "Deliver order", "type": "task", "actor": "Logistics"},
   {"name": "End", "type": "end"}
 ],
 "actors": ["Customer", "Sales", "Logistics"],
 "pains": ["Delays in stock availability", "Customer cancellations", "Payment errors"]
}
                    """},
                    {"role": "user", "content": input_text},
                ],
            )

            ai_output = response.choices[0].message.content.strip()

            # Intentar convertir a JSON
            try:
                data = json.loads(ai_output)
            except json.JSONDecodeError:
                st.error("⚠️ La IA devolvió texto no estructurado. Mostrando salida sin procesar:")
                st.text(ai_output)
                data = {}

            if data:
                steps = data.get("steps", [])
                actors = data.get("actors", [])
                pains = data.get("pains", [])

                tabs = st.tabs(["🗺️ Mapa BPMN", "📋 Detalle", "👥 Stakeholders", "⚠️ Pain Points"])

                # ==========================================
                # 🗺️ MAPA BPMN
                # ==========================================
                with tabs[0]:
                    dot = Digraph(format="svg")
                    dot.attr(rankdir="LR", size="10,5")

                    for step in steps:
                        node_type = step.get("type", "task")
                        label = step.get("name", "")
                        actor = step.get("actor", "")

                        if actor:
                            label += f"\n👤 {actor}"

                        if node_type == "start":
                            dot.node(label, shape="ellipse", style="filled", fillcolor="#4CAF50")
                        elif node_type == "end":
                            dot.node(label, shape="ellipse", style="filled", fillcolor="#37474F", fontcolor="white")
                        elif node_type == "decision":
                            dot.node(label, shape="diamond", style="filled", fillcolor="#FFB74D")
                        else:  # task
                            dot.node(label, shape="box", style="rounded,filled", fillcolor="#90CAF9")

                    # Conectar pasos secuenciales
                    for i in range(len(steps) - 1):
                        dot.edge(steps[i]["name"], steps[i + 1]["name"])

                    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".svg")
                    dot.render(tmpfile.name, cleanup=True)
                    st.image(tmpfile.name + ".svg")
                    os.remove(tmpfile.name + ".svg")

                # ==========================================
                # 📋 DETALLE
                # ==========================================
                with tabs[1]:
                    st.json(data)

                # ==========================================
                # 👥 STAKEHOLDERS
                # ==========================================
                with tabs[2]:
                    if actors:
                        st.dataframe(pd.DataFrame(actors, columns=["Stakeholders"]))
                    else:
                        st.info("No se detectaron actores.")

                # ==========================================
                # ⚠️ PAIN POINTS
                # ==========================================
                with tabs[3]:
                    if pains:
                        st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))
                    else:
                        st.info("No se detectaron problemas reportados.")

        except Exception as e:
            st.error(f"Error durante el análisis: {e}")
