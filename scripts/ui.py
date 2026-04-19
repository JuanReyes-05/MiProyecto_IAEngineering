"""Interfaz Streamlit para probar la API del helpdesk."""
import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Soporte AI — Helpdesk RAG",
    page_icon="🤖",
    layout="wide",
)

with st.sidebar:
    st.header("Configuración")
    api_url = st.text_input("API URL", value=DEFAULT_API)
    usuario_id = st.text_input("Usuario", value="mike.test")

    st.divider()
    st.subheader("Estado del backend")
    if st.button("Verificar /health", use_container_width=True):
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            r.raise_for_status()
            data = r.json()
            st.success(f"estado: {data.get('estado')}")
            st.json(data.get("estadisticas", {}))
        except Exception as e:
            st.error(f"No se pudo contactar la API: {e}")

    st.divider()
    if st.button("Limpiar conversación", use_container_width=True):
        st.session_state.historial = []
        st.rerun()

st.title("🤖 Soporte AI")
st.caption("Helpdesk con RAG sobre tu base de conocimiento.")

if "historial" not in st.session_state:
    st.session_state.historial = []

ACCION_BADGE = {
    "responder": ("✅", "Respuesta directa"),
    "derivar_ticket": ("📩", "Derivar a 2do nivel"),
    "escalar_humano": ("🚨", "Escalar a humano"),
}


def render_respuesta(data: dict):
    icon, label = ACCION_BADGE.get(data["accion"], ("❔", data["accion"]))
    cols = st.columns([2, 1, 1])
    cols[0].markdown(f"**{icon} {label}**")
    cols[1].metric("Confianza", f"{data['score_confianza']:.2f}")
    cols[2].metric("Fuentes", len(data.get("fuentes", [])))

    st.markdown(data["respuesta"])

    fuentes = data.get("fuentes", [])
    if fuentes and data.get("tiene_info", True):
        with st.expander(f"Ver {len(fuentes)} fuente(s)"):
            for i, f in enumerate(fuentes, 1):
                score = f.get("score")
                score_txt = f" — score {score:.3f}" if score is not None else ""
                st.markdown(f"**{i}. `{f['archivo']}`**{score_txt}")
                st.code(f["fragmento"], language="markdown")

    st.caption(
        f"modelo: `{data['modelo']}` · consulta: `{data['consulta_id']}` · {data['timestamp']}"
    )


for turno in st.session_state.historial:
    with st.chat_message("user"):
        st.markdown(turno["pregunta"])
    with st.chat_message("assistant"):
        render_respuesta(turno["respuesta"])

pregunta = st.chat_input("Escribe tu pregunta...")

if pregunta:
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando RAG..."):
            try:
                r = requests.post(
                    f"{api_url}/ask",
                    json={"pregunta": pregunta, "usuario_id": usuario_id},
                    timeout=60,
                )
                r.raise_for_status()
                data = r.json()
                render_respuesta(data)
                st.session_state.historial.append(
                    {"pregunta": pregunta, "respuesta": data}
                )
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                friendly = None
                if e.response is not None:
                    try:
                        body = e.response.json()
                        if status == 422 and isinstance(body.get("detail"), list):
                            msgs = []
                            for err in body["detail"]:
                                field = ".".join(str(p) for p in err.get("loc", [])[1:])
                                msgs.append(f"`{field}`: {err.get('msg', 'inválido')}")
                            friendly = "Validación fallida — " + "; ".join(msgs)
                        elif isinstance(body.get("detail"), str):
                            friendly = body["detail"]
                    except ValueError:
                        pass
                st.error(friendly or f"Error {status or ''}: {e.response.text if e.response is not None else str(e)}")
            except Exception as e:
                st.error(f"Falló la consulta: {e}")
