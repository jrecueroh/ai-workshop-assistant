import streamlit as st
from openai import OpenAI
import pandas as pd
import json

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

# ==========================================
# FUNCIÓN AUXILIAR
# ==========================================
def generate_mermaid(steps):
    """Genera un diagrama Mermaid estilo BPM."""
    mermaid = ["flowchart LR"]
    for i, step in enumerate(steps):
        name = step.get("name", f"Step {i+1}")
        node_type = step.get("type", "task")
        actor = step.get("actor", "")

        label = name
        if actor:
            label += f"\\n👤 {actor}"

        # Colores y formas BPMN-like
        if node_type == "start":
            mermaid.append(f'    A{i}(["{label}"]):::start')
        elif node_type == "end":
            mermaid.append(f'    A{i}(["{label}"]):::end')
        elif node_type == "decision":
            mermaid.append(f'    A{i}{{"{label}"}}:::decision')
        else:
            mermaid.append(f'    A{i}["{label}"]:::task')

        if i > 0:
            mermaid.append(f"    A{i-1} --> A{i}")

    # Estilos CSS en Mermaid
    mermaid.append("""
    classDef start fill:#4CAF50,color:#fff;
    classDef end fill:#37474F,color:#fff;
    classDef decision fill:#FFB74D,color:#000,stroke:#E65100;
    classDef task fill:#90CAF9,color:#000,stroke:#1565C0;
    """)

    return "\n".join(mermaid)

# ==========================================
# ANÁLISIS IA
# ==========================================
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
Analiza la descripción y devuelve un JSON simple con:
{
 "steps": [
   {"name": "Customer places order", "type": "task", "actor": "Customer"},
   {"name": "Product available?", "type": "decision"},
   {"name": "Process Payment", "type": "task", "actor": "Sales"},
   {"name": "Deliver order", "type": "task", "actor": "Logistics"},
   {"name": "End", "type": "end"}
 ],
 "actors": ["Customer", "Sales", "Logistics"],
 "pains": ["Delays in stock availability", "Customer cancellations"]
}
                    """},
                    {"role": "user", "content": input_text},
                ],
            )

            ai_output = response.choices[0].message.content.strip()

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

                tabs = st.tabs(["🗺️ Mapa BPMN", "📋 Estructura", "👥 Stakeholders", "⚠️ Pain Points"])

                # ==========================================
                # 🗺️ MAPA BPMN (MERMAID)
                # ==========================================
                with tabs[0]:
                    st.subheader("🗺️ Mapa de proceso estilo BPMN")
                    mermaid_code = generate_mermaid(steps)
                    st.markdown(f"```mermaid\n{mermaid_code}\n```")

                # ==========================================
                # 📋 JSON SIMPLE
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
                        st.info("No se detectaron problemas.")

        except Exception as e:
            st.error(f"Error durante el análisis: {e}")
