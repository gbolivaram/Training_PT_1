import streamlit as st
import html

# Configurar la página
st.set_page_config(
    page_title="Mi Primera App Streamlit",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🎉 Bienvenido a mi App Streamlit")

# Crear tabs para organizar el contenido
tab1, tab2, tab3 = st.tabs(["Inicio", "Formulario", "Información"])

with tab1:
    st.header("Pestaña de Inicio")
    st.write("Esta es tu primera aplicación con Streamlit, HTML y GitHub!")
    
    # Usar HTML personalizado
    st.markdown("""
    <div style="background-color:#f0f2f6; padding:20px; border-radius:10px;">
        <h3 style="color:#0066cc;">¿Qué es Streamlit?</h3>
        <p>Streamlit es un framework de Python que permite crear aplicaciones web interactivas 
        sin necesidad de conocer JavaScript o CSS avanzado.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar columnas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("📚 Aprende HTML")
    with col2:
        st.success("✅ Usa Streamlit")
    with col3:
        st.warning("🔧 Controla GitHub")

with tab2:
    st.header("Formulario Interactivo")
    
    # Elementos de entrada
    nombre = st.text_input("¿Cuál es tu nombre?", placeholder="Ingresa tu nombre aquí")
    edad = st.slider("¿Cuál es tu edad?", 0, 100, 25)
    ciudad = st.selectbox("¿De qué ciudad eres?", 
                         ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena"])
    
    # Botón para procesar
    if st.button("📤 Enviar Información"):
        if nombre:
            st.success(f"¡Hola {nombre}! Tienes {edad} años y eres de {ciudad}.")
            st.balloons()
        else:
            st.error("Por favor ingresa tu nombre")

with tab3:
    st.header("Información del Proyecto")
    
    st.markdown("""
    ### 📖 Temas Cubiertos:
    
    **1. HTML:**
    - Elementos básicos (div, p, h1-h6)
    - Estilos CSS (color, padding, border-radius)
    - Atributos personalizados
    
    **2. Streamlit UI:**
    - st.write() - para mostrar texto
    - st.columns() - para layouts
    - st.tabs() - para pestañas
    - st.slider(), st.text_input(), st.selectbox() - para entrada de datos
    - st.success(), st.error(), st.info() - para mensajes
    
    **3. GitHub:**
    - Versionado de código
    - Commits con mensajes descriptivos
    - Repositorios públicos
    
    ### 🎯 Próximos Pasos:
    1. Instala las dependencias
    2. Ejecuta: `streamlit run app.py`
    3. Experimenta con los componentes
    4. Realiza cambios y haz commits
    """)
    
    # Información de GitHub
    st.divider()
    st.subheader("Mi Repositorio en GitHub")
    st.write("Repositorio: **gbolivaram/Training_PT_1**")
    st.write("Lenguajes: Python, HTML, Markdown")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controles")
    st.write("Usa los controles anteriores en las pestañas para interactuar")
    
    with st.expander("📝 Ver Código Fuente"):
        st.code("""
# Este es un ejemplo de cómo está estructurado el código
import streamlit as st

st.title("Mi App")
st.write("Contenido")
        """, language="python")