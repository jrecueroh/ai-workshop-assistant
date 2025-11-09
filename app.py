import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import re
import html

# ==============================
# CONFIGURACIÓN
# ==============================
st.set_page_config(page_title="AI Workshop Assistant — BPM Visualizer", layout="wide")
st.title("🧩 AI Workshop Assistant — Business Process Visualizer")

st.markdown("""
Convierte tu descripción de proceso o workshop en un **mapa visual estilo BPMN**,  
junto con actores y problemas detectados automáticamente por IA.
""")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==============================
# LIMPIEZA DE TEXTO
# ==============================
def clean_label(text: str) -> str:
    """Limpia texto para Mermaid (sin saltos, acentos ni emojis)."""
    if not text:
        return ""
    text = html.escape(text)  # escapamos HTML
    text = re.sub(r"[\"'{}<>#|]", "", text)
    text = re.sub(r"[\n\r\t]", " ", text)
    text = re.sub(r"\s+", " ", text)
    # sustituir caracteres latinos extendidos por versiones ASCII seguras
    trans = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    text = text.translate(trans)
    return text.strip()

# ==============================
# GENERADOR DE MERMAID
# ==============================
def generate_mermaid(steps):
    mermaid = ["flowchart LR"]
    for i, step in enumerate(steps):
        name = clean_label(step.get("name", f"Step {i+1}"))
        node_type = step.get("type", "task")
        actor = clean_label(step.get("actor", ""))

        label = name
        if actor:
            label += f" ({actor})"

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

    mermaid.append("""
    classDef start fill:#4CAF50,color:#fff;
    classDef end fill:#37474F,color:#fff;
    classDef decision fill:#FFB74D,color:#000,stroke:#E65100;
    classDef task fill:#90CAF9,color:#000,stroke:#1565C0;
    """)
    return "\n".join(mermaid)

# ==============================
# INTERFAZ PRINCIPAL
# ==============================
input_text = st.text_area(
    "✏️ Pega la descripción del proceso",
    height=250,
    placeholder="Ejemplo: El cliente realiza un pedido, se verifica el stock, se factura y se entrega..."
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
Eres un experto en modelado BPMN. Devuelve JSON simple con:
{
 "steps": [
   {"name": "Inicio", "type": "start"},
   {"name": "Verificar stock", "type": "decision"},
   {"name": "Procesar pago", "type": "task", "actor": "Ventas"},
   {"name": "Entregar producto", "type": "task", "actor": "Logistica"},
   {"name": "Fin", "type": "end"}
 ],
 "actors": ["Ventas", "Logistica"],
 "pains": ["Errores en inventario", "Retrasos en entrega"]
}
                    """},
                    {"role": "user", "content": input_text},
                ],
            )

            ai_output = response.choices[0].message.content.strip()
            try:
                data = json.loads(ai_output)
            except Exception:
                st.warning("⚠️ La IA devolvió texto no estructurado.")
                st.code(ai_output)
                data = {}

            if not data:
                st.stop()

            steps = data.get("steps", [])
            actors = data.get("actors", [])
            pains = data.get("pains", [])

            tabs = st.tabs(["🗺️ Mapa Visual", "📋 Estructura", "👥 Actores", "⚠️ Problemas"])

            # ==============================
            # 🗺️ MAPA VISUAL
            # ==============================
            with tabs[0]:
                st.subheader("🧩 Mapa visual del proceso")
                mermaid_code = generate_mermaid(steps)
                try:
                    st.components.v1.html(
                        f"""
                        <div class="mermaid">
                        {mermaid_code}
                        </div>
                        <script type="module">
                          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                          mermaid.initialize({{ startOnLoad: true, theme: "neutral", securityLevel: "loose" }});
                        </script>
                        """,
                        height=700,
                    )
                except Exception as e:
                    st.error(f"❌ Error al renderizar Mermaid: {e}")
                    st.code(mermaid_code)

            # ==============================
            # 📋 JSON
            # ==============================
            with tabs[1]:
                st.json(data)

            # ==============================
            # 👥 ACTORES
            # ==============================
            with tabs[2]:
                if actors:
                    st.dataframe(pd.DataFrame(actors, columns=["Stakeholders"]))
                else:
                    st.info("No se detectaron actores.")

            # ==============================
            # ⚠️ PROBLEMAS
            # ==============================
            with tabs[3]:
                if pains:
                    st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))
                else:
                    st.info("No se detectaron problemas.")

        except Exception as e:
            st.error(f"Error durante el análisis: {e}")
