import streamlit as st
from openai import OpenAI
import pandas as pd
from pyvis.network import Network
import json
import tempfile
import os

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="AI Workshop Assistant", layout="wide")
st.title("🤖 AI Workshop Assistant — Mapeador Inteligente de Procesos")

st.markdown("""
Esta herramienta te ayuda a analizar **workshops o descripciones de procesos empresariales**  
y convertirlos automáticamente en **diagramas, estructuras de datos y reportes**.
""")

# Inicializar cliente de OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==========================================
# ENTRADA DE USUARIO
# ==========================================
input_text = st.text_area(
    "🗒️ Pega aquí la transcripción o descripción de tu workshop",
    height=250,
    placeholder="Ejemplo: Tenemos cuatro plantas de producción distribuidas en diferentes países..."
)

analyze_btn = st.button("🔍 Analizar Workshop")

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def generate_process_map(json_data):
    """Crea un gráfico interactivo de procesos con PyVis."""
    net = Network(height="550px", width="100%", bgcolor="#f8f9fa", font_color="#222", directed=True)
    net.barnes_hut()
    steps = json_data.get("steps", [])

    for step in steps:
        name = step.get("name", "Paso")
        actor = step.get("actor", "Desconocido")
        label = f"{name}\n👤 {actor}"
        net.add_node(name, label=label, shape="box", color="#90CAF9")

    for i in range(len(steps) - 1):
        net.add_edge(steps[i].get("name"), steps[i + 1].get("name"))

    return net


def display_dataframes(json_data):
    """Muestra tablas estructuradas en pestañas."""
    steps = json_data.get("steps", [])
    actors = json_data.get("actors", [])
    pains = json_data.get("pains", [])

    with st.expander("📋 Detalle de pasos del proceso"):
        if steps:
            st.dataframe(pd.DataFrame(steps))
        else:
            st.info("No se detectaron pasos.")

    with st.expander("👥 Actores identificados"):
        if actors:
            st.dataframe(pd.DataFrame(actors, columns=["Actor"]))
        else:
            st.info("No se detectaron actores.")

    with st.expander("⚠️ Problemas y pain points"):
        if pains:
            st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))
        else:
            st.info("No se detectaron pains.")


def save_html_map(network):
    """Guarda el gráfico PyVis en un archivo temporal y lo muestra."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        network.save_graph(tmp_file.name)
        return tmp_file.name

# ==========================================
# ANÁLISIS CON IA
# ==========================================
if analyze_btn and input_text.strip():
    with st.spinner("⏳ Analizando tu workshop con IA..."):
        try:
            # Llamada al modelo
            resp = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "Eres un consultor experto en procesos empresariales. Analiza y devuelve el resultado en JSON estructurado con 'steps', 'actors', 'inputs', 'outputs', y 'pains'."},
                    {"role": "user", "content": input_text},
                ],
            )

            ai_text = resp.choices[0].message.content.strip()

            # Intentar convertir la respuesta en JSON
            try:
                json_data = json.loads(ai_text)
            except json.JSONDecodeError:
                st.warning("⚠️ La IA devolvió texto, no JSON. Mostrando salida sin procesar.")
                st.text(ai_text)
                json_data = {}

            # Mostrar resultados
            if json_data:
                tabs = st.tabs(["📊 Estructura JSON", "🗺️ Mapa Visual", "📑 Tablas Detalladas", "🧠 Insights del Proceso"])

                with tabs[0]:
                    st.json(json_data)

                with tabs[1]:
                    net = generate_process_map(json_data)
                    html_path = save_html_map(net)
                    with open(html_path, "r", encoding="utf-8") as f:
                        st.components.v1.html(f.read(), height=600, scrolling=True)
                    os.remove(html_path)

                with tabs[2]:
                    display_dataframes(json_data)

                with tabs[3]:
                    st.markdown("### 🧠 Análisis de la IA")
                    st.write("Basado en los datos extraídos, la IA puede sugerir optimizaciones o mejoras futuras en los procesos.")
                    st.info("✨ Ejemplo: Digitalizar la comunicación entre plantas para reducir errores de integración SAP.")

        except Exception as e:
            st.error(f"Error en el análisis o conexión con la API: {e}")
else:
    st.info("Pega la descripción de tu workshop arriba y haz clic en **Analizar Workshop**.")
