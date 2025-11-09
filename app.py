import streamlit as st
from openai import OpenAI
import json
import re
from textwrap import dedent
import io
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Configuración de la página
st.set_page_config(page_title="AI Workshop Assistant", layout="wide")
st.title("AI Workshop Assistant — Generador de mapas (Mermaid)")

st.markdown("""
Pega aquí la transcripción o descripción de tu workshop.  
La herramienta generará un **diagrama Mermaid** y un **resumen estructurado**.
""")

# ===== Configuración =====
USE_MOCK = True  # Cambia a False cuando tengas crédito
if not USE_MOCK:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Área de texto
input_text = st.text_area("Transcripción / Descripción", height=250)

# ===== Función principal =====
def generar_resumen_y_diagrama(texto):
    if USE_MOCK:
        # Respuesta simulada para pruebas
        parsed = {
            "steps": ["Inicio", "Compras de materiales", "Producción", "Control de calidad", "Entrega"],
            "actors": ["Gerente", "Departamento de Compras", "Supervisor de Producción", "Calidad", "Logística"],
            "inputs": ["Solicitudes", "Materiales"],
            "outputs": ["Producto terminado"],
            "pains": ["Retrasos en compras", "Fallas en producción"]
        }
        mermaid_code = dedent("""
        flowchart TD
            A0["Inicio"] --> A1["Compras de materiales"]
            A1 --> A2["Producción"]
            A2 --> A3["Control de calidad"]
            A3 --> A4["Entrega"]
        """).strip()
        return parsed, mermaid_code

    # Código real de OpenAI
    prompt = dedent(f"""
    Eres un asistente experto en mapear procesos. Extrae pasos, actores, inputs, outputs y pain points del texto:
    \"\"\"{texto}\"\"\"
    Devuelve JSON con claves: steps, actors, inputs, outputs, pains
    """)
    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en procesos de negocio."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )
    except Exception as e:
        st.warning(f"Error en la API de OpenAI: {e}")
        return None, None

    content = resp.choices[0].message.content
    m = re.search(r"\{.*\}", content, re.S)
    parsed = json.loads(m.group(0)) if m else {"steps":[], "actors":[], "inputs":[], "outputs":[], "pains":[content]}

    # Mermaid
    steps = parsed.get("steps", [])
    mermaid = ["flowchart TD"]
    for i, s in enumerate(steps):
        node = f"A{i}"
        mermaid.append(f'    {node}["{s}"]')
        if i > 0:
            mermaid.append(f'    A{i-1} --> {node}')
    mermaid_code = "\n".join(mermaid)

    return parsed, mermaid_code

# ===== Botón de generación =====
if st.button("Generar mapa"):
    if not input_text.strip():
        st.warning("Pega algo de texto primero.")
        st.stop()

    with st.spinner("Generando..."):
        resumen, mermaid = generar_resumen_y_diagrama(input_text)

    if resumen:
        st.subheader("Resumen JSON")
        st.json(resumen)

        st.subheader("Diagrama Mermaid")
        st.markdown("```mermaid\n" + mermaid + "\n```")

        # Botón para exportar PDF simple
        if st.button("Exportar PDF"):
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            text_obj = c.beginText(40, 800)
            text_obj.setFont("Helvetica", 10)
            text_obj.textLine("AI Workshop Assistant - Export")
            text_obj.textLine("")
            text_obj.textLine("Resumen:")
            c.drawText(text_obj)
            c.drawString(40, 760, str(resumen))
            c.showPage()
            c.save()
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="workshop_export.pdf">Descargar PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
