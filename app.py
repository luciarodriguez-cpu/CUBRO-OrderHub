"""
app.py — Order Hub CUBRO
Orquestación Streamlit del flujo A → B → C → B.
"""

import os
import subprocess
from datetime import datetime

import pandas as pd
import streamlit as st

import modulo_a
import modulo_b
import modulo_c
from modulo_b import PANTALLA_VALIDACION, PANTALLA_PASO_1, PANTALLA_PASO_2


# Módulo A ya implementado — lee catalogo.json y opciones_mueble.yaml en tiempo real.
USE_MOCK_DATA = False

# Módulo C implementado — ya no se usa el mock.
USE_MOCK_C = False


def _default_state() -> dict:
    return {
        "pantalla": PANTALLA_VALIDACION,
        "csv_filename": None,
        "csv_uploaded_at": None,
        "muebles": None,
        "selecciones_paso_1": {},
        "pedido_paso_2": None,
        "entrada_modulo_c": None,
        "pending_csv": None,
        "uploader_nonce": 0,
        "csv_fallback_a_mock": False,
    }


def _init_session_state() -> None:
    for key, value in _default_state().items():
        st.session_state.setdefault(key, value)


def _hay_progreso() -> bool:
    selecciones = st.session_state.get("selecciones_paso_1") or {}
    for mueble in selecciones.values():
        if mueble.get("check") or mueble.get("opcionales"):
            return True
    return False


def _mock_muebles() -> list[dict]:
    return [
        {
            "Name": "B608035",
            "Name SKP": "B608035-1",
            "Estado": "✅ CORRECTO",
            "Apertura": "1",
            "D_Gama": "1",
            "ColorFrente": "Crema LACA",
            "Color del interior": "Blanco mueble",
            "Tirador": "2",
            "Trasera": "Laca",
            "Color tir. de superficie": "Inox",
            "C_Rodapietext": "100 mm",
            "Ancho": "600 mm",
            "Ancho reducido": "",
            "LenZ": "800",
            "Color del mueble abierto": "",
            "Avisos": "",
        },
        {
            "Name": "H1.60",
            "Name SKP": "H1-60-1",
            "Estado": "✅ CORRECTO",
            "Apertura": "2",
            "D_Gama": "2",
            "ColorFrente": "Oak WOOD",
            "Color del interior": "Roble mueble",
            "Tirador": "20",
            "Trasera": "Oak WOOD",
            "Color tir. de superficie": "",
            "C_Rodapietext": "0 mm",
            "Ancho": "600 mm",
            "Ancho reducido": "",
            "LenZ": "720",
            "Color del mueble abierto": "",
            "Avisos": "",
        },
        {
            "Name": "",
            "Name SKP": "MUEBLE-CON-ERROR",
            "Estado": "⚠️ REVISAR",
            "Apertura": "",
            "D_Gama": "",
            "ColorFrente": "",
            "Color del interior": "",
            "Tirador": "",
            "Trasera": "",
            "Color tir. de superficie": "",
            "C_Rodapietext": "",
            "Ancho": "10000 mm",
            "Ancho reducido": "",
            "LenZ": "",
            "Color del mueble abierto": "",
            "Avisos": "A02 | A17",
        },
        {
            "Name": "EOV9060",
            "Name SKP": "EOV9060-1",
            "Summary": "M4",
            "Estado": "✅ CORRECTO",
            "Apertura": "",
            "D_Gama": "",
            "ColorFrente": "",
            "Color del interior": "",
            "Tirador": "",
            "Trasera": "",
            "Color tir. de superficie": "",
            "C_Rodapietext": "100 mm",
            "Ancho": "600 mm",
            "Ancho reducido": "",
            "LenZ": "900",
            "Color del mueble abierto": "Oak WOOD",
            "Avisos": "",
        },
    ]


# Columnas booleanas de la entrada que se exponen como "Sí" en el bloque
# "Opciones adicionales" del Paso 2 cuando el usuario las ha marcado.
_OPCIONALES_BOOL_EN_ENTRADA = (
    "Sin mecanizado",
    "Cubos de basura",
    "Recorte LED",
    "Cajón interior",
    "Mueble de caldera",
    "Sin encolar",
)


def _mock_pedido(muebles: list[dict], entrada: list[dict]) -> list[dict]:
    """Mock del Módulo C — consume la entrada de Paso 1 (CLAUDE.md §9).

    Devuelve la misma list[dict] que espera el Paso 2: cada entrada extiende
    el dict del mueble original con:
      - opciones_adicionales: list[dict] {etiqueta, valor, origen}
      - codigos_sg: dict[op_id, valor]
    """
    pedido: list[dict] = []
    for mueble, fila in zip(muebles, entrada):
        opciones_adicionales: list[dict] = []

        for col in _OPCIONALES_BOOL_EN_ENTRADA:
            if fila.get(col) == "True":
                opciones_adicionales.append(
                    {"etiqueta": col, "valor": "Sí", "origen": "usuario"}
                )

        sensor = fila.get("Sensor para mando LED", "")
        if sensor:
            opciones_adicionales.append(
                {
                    "etiqueta": "Sensor para mando LED",
                    "valor": sensor,
                    "origen": "usuario",
                }
            )

        electro_partes = [
            fila.get("Marca electro", ""),
            fila.get("Referencia electro", ""),
            fila.get("Alto electro", ""),
        ]
        electro_partes = [p for p in electro_partes if p]
        if electro_partes:
            opciones_adicionales.append(
                {
                    "etiqueta": "Electrodoméstico",
                    "valor": " · ".join(electro_partes),
                    "origen": "usuario",
                }
            )

        # Forzada de ejemplo para que el marcador ⚙ sea visible en el Paso 2.
        opciones_adicionales.append(
            {
                "etiqueta": "Mecanizado tirador",
                "valor": "Estándar (FSP)",
                "origen": "automatico",
            }
        )

        pedido.append(
            {
                **mueble,
                "opciones_adicionales": opciones_adicionales,
                "codigos_sg": {
                    "op_100": "L",
                    "op_101": "CR",
                    "op_300": "Q2",
                    "op_402": "P10",
                },
            }
        )
    return pedido


def _calcular_pedido_paso_2() -> list[dict]:
    """Construye la entrada del Módulo B y la procesa con el Módulo C."""
    muebles = st.session_state.muebles or []
    selecciones = st.session_state.selecciones_paso_1 or {}
    catalogo = modulo_b._cargar_catalogo()
    entrada = modulo_b.construir_entrada_modulo_c(muebles, selecciones, catalogo)
    st.session_state.entrada_modulo_c = entrada
    # Invalidar export anterior: el pedido se recalcula, los archivos deben regenerarse
    st.session_state.pop("_export_excel", None)
    st.session_state.pop("_export_json", None)
    if USE_MOCK_C:
        return _mock_pedido(muebles, entrada)
    return modulo_c.calcular_opciones(entrada) or []


# Schema del output del Módulo A (ver CLAUDE.md §9).
_COLUMNAS_OUTPUT_MODULO_A = {
    "Name", "Name SKP", "Estado", "Apertura", "D_Gama", "ColorFrente",
    "Color del interior", "Tirador", "Trasera", "Color tir. de superficie",
    "C_Rodapietext", "Ancho", "Ancho reducido", "LenZ", "Avisos",
    # "Color del mueble abierto" es opcional (no en todos los CSVs) — no se incluye en la check
}


def _parsear_csv_output_modulo_a(file) -> list[dict] | None:
    # Workaround mientras modulo_a.parsear_csv siga siendo stub: si el CSV
    # subido ya es el output del Módulo A (mismas columnas), lo usamos
    # directamente. Devuelve None si el schema no coincide.
    try:
        df = pd.read_csv(file, dtype=str).fillna("")
    except Exception:
        return None
    if not _COLUMNAS_OUTPUT_MODULO_A.issubset(df.columns):
        return None
    return df.to_dict("records")


def _cargar_csv(file) -> None:
    st.session_state.csv_filename = file.name
    st.session_state.csv_uploaded_at = datetime.now()
    st.session_state.selecciones_paso_1 = {}
    st.session_state.pedido_paso_2 = None
    st.session_state.pantalla = PANTALLA_VALIDACION
    st.session_state.csv_fallback_a_mock = False
    st.session_state.pop("paso_1_abiertos", None)  # forzar re-inicialización con todas las cards abiertas

    if not USE_MOCK_DATA:
        # Detectar si es el CSV de validación ya procesado (output del Módulo A),
        # no el CSV original de SketchUp. Columnas exclusivas del output: Estado, Name SKP, Avisos.
        _COLUMNAS_OUTPUT_A = {"Estado", "Name SKP", "Avisos"}
        try:
            _contenido = file.read()
            if isinstance(_contenido, bytes):
                _contenido = _contenido.decode("utf-8-sig")
            import io as _io
            _cols = set(pd.read_csv(_io.StringIO(_contenido), nrows=0, dtype=str).columns)
            file.seek(0)
        except Exception:
            _cols = set()
            file.seek(0)

        if _cols & _COLUMNAS_OUTPUT_A:
            st.session_state.muebles = []
            st.session_state["_error_csv"] = (
                "El archivo subido es el CSV ya validado por el Módulo A, no el original de SketchUp. "
                "Sube el archivo exportado directamente desde SketchUp con la plantilla CUBRO x SG.grt."
            )
            return

        resultado = modulo_a.parsear_csv_para_modulo_b(file)
        if not resultado["ok"]:
            st.session_state.muebles = []
            st.session_state["_error_csv"] = resultado["error_archivo"]
        else:
            muebles = resultado["muebles"]
            for i, m in enumerate(muebles):
                m["_pos"] = i   # índice de posición fijo — garantiza keys únicas incluso si dos muebles tienen el mismo Name
            st.session_state.muebles = muebles
            st.session_state.pop("_error_csv", None)
        return

    muebles_reales = _parsear_csv_output_modulo_a(file)
    if muebles_reales is not None:
        st.session_state.muebles = muebles_reales
    else:
        st.session_state.muebles = _mock_muebles()
        st.session_state.csv_fallback_a_mock = True


def _reset_completo() -> None:
    nonce = st.session_state.get("uploader_nonce", 0) + 1
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_session_state()
    # Cambiar la key del uploader fuerza a Streamlit a redibujarlo vacío.
    st.session_state.uploader_nonce = nonce


def _fecha_ultimo_commit() -> str | None:
    try:
        salida = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%d/%m/%Y"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=5,
        )
        fecha = salida.stdout.strip()
        return fecha or None
    except Exception:
        return None


def _render_fecha_ultima_actualizacion() -> None:
    fecha = _fecha_ultimo_commit()
    if not fecha:
        return
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 6px; left: 10px; font-size: 0.7rem; color: gray; z-index: 100;">
            Última actualización: {fecha}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.image("assets/Logo CUBRO_positivo.png", use_container_width=True)
        _MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
        hoy = datetime.today()
        st.caption(f"{hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}")

        st.divider()

        uploader_key = f"csv_uploader_{st.session_state.uploader_nonce}"
        nuevo = st.file_uploader(
            "Sube el CSV exportado desde SketchUp",
            type=["csv"],
            key=uploader_key,
        )

        if nuevo is not None and nuevo.name != st.session_state.csv_filename:
            if _hay_progreso():
                st.session_state.pending_csv = nuevo
            else:
                _cargar_csv(nuevo)
                st.rerun()

        if st.session_state.csv_filename:
            st.divider()
            st.markdown(f"**Archivo:** `{st.session_state.csv_filename}`")
            st.markdown(
                f"**Subido:** {st.session_state.csv_uploaded_at:%d/%m/%Y %H:%M}"
            )
            n_muebles = len(st.session_state.muebles or [])
            st.markdown(f"**Muebles detectados:** {n_muebles}")

            if st.button("Subir otro CSV", use_container_width=True):
                if _hay_progreso():
                    st.session_state.pending_csv = "reset"
                else:
                    _reset_completo()
                    st.rerun()


def _render_modal_reemplazo() -> None:
    pending = st.session_state.get("pending_csv")
    if pending is None:
        return

    st.warning(
        "Vas a reemplazar el CSV cargado. Se perderá el progreso del Paso 1."
    )
    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("Reemplazar y perder progreso", type="primary"):
            if pending == "reset":
                _reset_completo()
            else:
                _cargar_csv(pending)
            st.session_state.pending_csv = None
            st.rerun()
    with col_cancel:
        if st.button("Cancelar"):
            st.session_state.pending_csv = None
            # Reiniciar el uploader para que olvide el fichero seleccionado.
            # Sin esto, la sidebar vuelve a detectar el nuevo CSV y reabre el modal.
            st.session_state.uploader_nonce = st.session_state.get("uploader_nonce", 0) + 1
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Order Hub CUBRO",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session_state()
    _render_fecha_ultima_actualizacion()

    # modulo_b puede solicitar un reset completo desde la Pantalla 0.
    if st.session_state.pop("_reset_requested", False):
        _reset_completo()
        st.rerun()

    _render_sidebar()

    if st.session_state.get("pending_csv") is not None:
        _render_modal_reemplazo()
        return

    if st.session_state.muebles is None:
        st.markdown(
            "<h1 style='color: purple;'>Order Hub CUBRO</h1>",
            unsafe_allow_html=True,
        )
        st.info("Sube un CSV exportado desde SketchUp en la barra lateral para comenzar.")
        return

    if st.session_state.get("csv_fallback_a_mock"):
        st.warning(
            "El CSV no coincide con el output esperado del Módulo A — "
            "se están usando datos mock para que puedas seguir probando."
        )

    # Error de archivo detectado por el Módulo A (columnas faltantes, etc.)
    if st.session_state.get("_error_csv"):
        st.error(f"❌ El archivo CSV no es válido: {st.session_state['_error_csv']}")
        st.info("Comprueba que has exportado el CSV con la plantilla correcta (CUBRO x SG.grt).")
        return

    pantalla = st.session_state.pantalla
    if pantalla == PANTALLA_VALIDACION:
        modulo_b.pantalla_validacion(st.session_state.muebles)
    elif pantalla == PANTALLA_PASO_1:
        modulo_b.paso_1(st.session_state.muebles)
    elif pantalla == PANTALLA_PASO_2:
        if st.session_state.pedido_paso_2 is None:
            st.session_state.pedido_paso_2 = _calcular_pedido_paso_2()
        modulo_b.paso_2(st.session_state.pedido_paso_2)


if __name__ == "__main__":
    main()
