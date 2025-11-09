import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import io
from pyvis.network import Network
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ========================================
# CONFIGURACIÓN INICIAL
# ========================================
st.set_page_config(
    page_title="AI Workshop Assistant PRO+",
    page_icon="🧭",
    layout="wide",
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🧭 AI Workshop Assistant PRO+")
st.markdown("""
Convierte descripciones de workshops o procesos complejos en **mapas interactivos, insights estructurados, KPIs y reportes profesionales.**
""")

# ========================================
# INPUT DE TEXTO
# ========================================
text = st.text_area(
    "📋 Pega aquí la transcripción o descripción del workshop:",
    placeholder="Ejemplo: En la planta de producción tenemos 4 líneas, una de mezclado, una de empaquetado...",
    height=200
)

# ========================================
# BOTÓN PRINCIPAL
# ========================================
if st.button("🚀 Analizar Workshop"):
    with st.spinner("Analizando con IA... ⏳"):
        prompt = f"""
        Eres un consultor experto en transformación de procesos empresariales.
        A partir del siguiente texto, identifica:
        - Los pasos principales del proceso
        - Los actores involucrados
        - Los inputs, outputs y pain points
        - Los KPIs relevantes
        - Un resumen ejecutivo
        Devuelve un JSON estructurado con:
        steps[], actors[], inputs[], outputs[], pains[], kpis[], summary
        Texto: {text}
        """

        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en optimización de procesos."},
                    {"role": "user", "content": prompt}
                ]
            )
            data = response.choices[0].message.content.strip()

            # Limpieza de JSON
            try:
                result = json.loads(data)
            except json.JSONDecodeError:
                st.warning("El resultado no es JSON puro, intentando limpiar...")
                cleaned = data[data.find("{"):data.rfind("}") + 1]
                result = json.loads(cleaned)

            st.success("✅ Análisis completado correctamente")

            # ========================================
            # TABS DEL DASHBOARD
            # ========================================
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "🗺️ Mapa Visual",
                "📋 Tablas",
                "📈 KPIs",
                "💡 Insights",
                "🔥 Pain Points (Heatmap)",
                "📦 Exportar"
            ])

            # --- TAB 1: VISUAL MAP ---
            with tab1:
                st.subheader("🗺️ Mapa Interactivo del Proceso")
                net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
                steps = result.get("steps", [])
                for i, step in enumerate(steps):
                    name = step.get("name", f"Paso {i+1}")
                    actor = step.get("actor", "Desconocido")
                    net.add_node(i, label=f"{name}\n({actor})", title=step.get("description", ""))
                    if i > 0:
                        net.add_edge(i - 1, i)
                net.save_graph("/mount/src/ai-workshop-assistant/process_map.html")
                st.components.v1.html(open("/mount/src/ai-workshop-assistant/process_map.html").read(), height=600)

            # --- TAB 2: TABLAS ---
            with tab2:
                st.subheader("📋 Pasos del Proceso")
                st.dataframe(pd.DataFrame(result.get("steps", [])))
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🎭 Actores")
                    st.dataframe(pd.DataFrame(result.get("actors", []), columns=["Actor"]))
                with col2:
                    st.subheader("⚙️ Inputs / Outputs")
                    st.dataframe(pd.DataFrame({
                        "Inputs": result.get("inputs", []),
                        "Outputs": result.get("outputs", [])
                    }))

            # --- TAB 3: KPIs ---
            with tab3:
                st.subheader("📈 Indicadores Clave (KPIs)")
                kpis = result.get("kpis", [])
                if kpis:
                    st.dataframe(pd.DataFrame(kpis, columns=["KPI"]))
                else:
                    st.info("No se detectaron KPIs. Añade datos de rendimiento o tiempos al texto para detectarlos.")

            # --- TAB 4: INSIGHTS ---
            with tab4:
                st.subheader("💡 Resumen Ejecutivo")
                st.write(result.get("summary", "Sin resumen disponible."))
                st.markdown("**Recomendaciones:** Usa los pain points y KPIs para planificar acciones de mejora.")

            # --- TAB 5: HEATMAP DE PAINS ---
            with tab5:
                st.subheader("🔥 Pain Points Detectados")
                pains = result.get("pains", [])
                if pains:
                    df_pains = pd.DataFrame(pains, columns=["Pain Point"])
                    st.dataframe(df_pains.style.background_gradient(cmap="Reds"))
                else:
                    st.info("No se detectaron pain points significativos.")

            # --- TAB 6: EXPORTAR ---
            with tab6:
                st.subheader("📦 Exportar Resultados")

                # JSON
                json_data = json.dumps(result, indent=4)
                st.download_button("💾 Descargar JSON", json_data, "analysis.json")

                # CSV
                csv_data = pd.DataFrame(result.get("steps", [])).to_csv(index=False)
                st.download_button("📊 Descargar CSV", csv_data, "steps.csv")

                # PDF
                if st.button("🧾 Generar PDF Profesional"):
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=A4)
                    styles = getSampleStyleSheet()
                    story = [Paragraph("AI Workshop Assistant Report", styles["Title"]), Spacer(1, 12)]
                    story.append(Paragraph("Resumen Ejecutivo:", styles["Heading2"]))
                    story.append(Paragraph(result.get("summary", ""), styles["Normal"]))
                    story.append(Spacer(1, 12))
                    story.append(Paragraph("Pain Points:", styles["Heading2"]))
                    for p in result.get("pains", []):
                        story.append(Paragraph(f"- {p}", styles["Normal"]))
                    doc.build(story)
                    st.download_button("📥 Descargar PDF", buffer.getvalue(), "workshop_report.pdf")

        except Exception as e:
            st.error(f"Error en el análisis o conexión con la API: {e}")
