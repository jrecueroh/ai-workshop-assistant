import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import plotly.graph_objects as go

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="AI Workshop Assistant — Visual BPM", layout="wide")
st.title("🧩 AI Workshop Assistant — Business Process Visualizer (Stable Plotly Version)")

st.markdown("""
Convierte tu descripción de proceso o workshop en un **mapa visual tipo BPM**,  
sin errores de Mermaid ni dependencias externas.
""")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==========================================
# FUNCIÓN PARA GENERAR DIAGRAMA VISUAL
# ==========================================
def draw_process_map(steps):
    """Dibuja un mapa de proceso horizontal con Plotly."""
    fig = go.Figure()

    # Colores por tipo
    colors = {
        "start": "#4CAF50",
        "end": "#37474F",
        "decision": "#FFB74D",
        "task": "#90CAF9"
    }

    x_pos = 0
    y_pos = 0
    step_positions = []

    for i, step in enumerate(steps):
        label = step.get("name", f"Step {i+1}")
        actor = step.get("actor", "")
        node_type = step.get("type", "task")

        text = f"{label}"
        if actor:
            text += f"<br><i>{actor}</i>"

        color = colors.get(node_type, "#90CAF9")

        fig.add_shape(
            type="rect",
            x0=x_pos,
            y0=y_pos,
            x1=x_pos + 1.5,
            y1=y_pos + 0.7,
            line=dict(color="black"),
            fillcolor=color,
        )

        fig.add_annotation(
            x=x_pos + 0.75,
            y=y_pos + 0.35,
            text=text,
            showarrow=False,
            font=dict(size=12, color="black"),
        )

        step_positions.append((x_pos, y_pos))
        x_pos += 2

    # Dibujar flechas
    for i in range(len(step_positions) - 1):
        x0, y0 = step_positions[i][0] + 1.5, step_positions[i][1] + 0.35
        x1, y1 = step_positions[i + 1][0], step_positions[i + 1][1] + 0.35
        fig.add_annotation(
            x=x1,
            y=y1,
            ax=x0,
            ay=y0,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="gray",
        )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        height=400,
        plot_bgcolor="white",
        margin=dict(l=50, r=50, t=50, b=50),
    )

    return fig

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
input_text = st.text_area(
    "✏️ Describe tu proceso:",
    height=250,
    placeholder="Ejemplo: El cliente realiza un pedido, se verifica el stock, se factura y se entrega."
)

if st.button("🚀 Analizar y generar mapa visual"):
    if not input_text.strip():
        st.warning("Por favor ingresa una descripción del proceso.")
        st.stop()

    with st.spinner("Analizando proceso con IA..."):
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": """
Eres un experto en modelado de procesos (BPM). 
Devuelve un JSON con una lista de pasos, tipo y actor.
Ejemplo:
{
 "steps": [
   {"name": "Inicio", "type": "start"},
   {"name": "Verificar stock", "type": "decision"},
   {"name": "Procesar pago", "type": "task", "actor": "Ventas"},
   {"name": "Entregar producto", "type": "task", "actor": "Logística"},
   {"name": "Fin", "type": "end"}
 ],
 "actors": ["Ventas", "Logística"],
 "pains": ["Errores de inventario", "Retrasos en entrega"]
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

            tabs = st.tabs(["🗺️ Mapa Visual", "📋 JSON", "👥 Actores", "⚠️ Problemas"])

            with tabs[0]:
                st.subheader("🧩 Mapa visual del proceso")
                if steps:
                    fig = draw_process_map(steps)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se detectaron pasos para graficar.")

            with tabs[1]:
                st.json(data)

            with tabs[2]:
                if actors:
                    st.dataframe(pd.DataFrame(actors, columns=["Stakeholders"]))
                else:
                    st.info("No se detectaron actores.")

            with tabs[3]:
                if pains:
                    st.dataframe(pd.DataFrame(pains, columns=["Pain Points"]))
                else:
                    st.info("No se detectaron problemas.")

        except Exception as e:
            st.error(f"Error durante el análisis: {e}")
