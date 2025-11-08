import streamlit as st
import openai
import os
import json
from textwrap import dedent
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="AI Workshop Assistant", layout="wide")
st.title("AI Workshop Assistant — Generador de mapas (Mermaid)")

st.markdown("""
Pega aquí la transcripción o descripción de tu workshop.
La herramienta generará un **diagrama Mermaid** y un resumen estructurado.
""")

# OpenAI API key desde Streamlit Cloud Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

input_text = st.text_area("Transcripción / Descripción", height=250)

if st.button("Generar mapa"):
    if not input_text.strip():
        st.warning("Pega algo de texto primero.")
        st.stop()

    with st.spinner("Generando..."):
        prompt = dedent(f"""
        Eres un asistente experto en mapear procesos. A partir del siguiente texto, extrae:
        1) Una lista de pasos secuenciales (ordenados) con frases cortas.
        2) Actores/roles principales.
        3) Entradas y salidas.
        4) Pain points/observaciones.
        Devuélvelo en JSON con claves: steps (lista), actors (lista), inputs (lista), outputs (lista), pains (lista).
        TEXT:
        \"\"\"{input_text}\"\"\"
        """)
        resp = openai.ChatCompletion.create(
            model="gpt-5-mini",
            messages=[{"role":"system","content":"Eres un experto en procesos de negocio."},
                      {"role":"user","content": prompt}],
            temperature=0.0,
            max_tokens=800
        )
        content = resp['choices'][0]['message']['content']

        import re
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            parsed = json.loads(m.group(0))
        else:
            parsed = {"steps":[],"actors":[],"inputs":[],"outputs":[],"pains":[content]}

        # Generar Mermaid
        steps = parsed.get("steps", [])
        mermaid = ["flowchart TD"]
        for i, s in enumerate(steps):
            node = f"A{i}"
            mermaid.append(f'    {node}["{s}"]')
            if i > 0:
                mermaid.append(f'    A{i-1} --> {node}')
        mermaid_code = "\n".join(mermaid)

    st.subheader("Resumen estructurado")
    st.json(parsed)

    st.subheader("Diagrama Mermaid")
    st.markdown("```mermaid\n" + mermaid_code + "\n```")

    if st.button("Exportar PDF (simple)"):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        text = c.beginText(40, 800)
        text.setFont("Helvetica", 10)
        text.textLine("AI Workshop Assistant - Export")
        text.textLine("")
        text.textLine("Resumen:")
        c.drawText(text)
        c.drawString(40,760, str(parsed))
        c.showPage()
        c.save()
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="workshop_export.pdf">Descargar PDF</a>'
        st.markdown(href, unsafe_allow_html=True)
