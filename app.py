import streamlit as st

st.set_page_config(
    page_title="Aperture — Image Forensic Analysis",
    layout="wide",
)

with st.sidebar:
    st.title("Aperture")
    st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "tiff", "bmp"])
    st.selectbox("Example image", ["(none)"])
    with st.expander("Settings"):
        st.write("Settings will appear here.")

tab_labels = ["Verdict", "AI Detection", "Tampering", "Scene", "Metadata", "Model Performance"]
tabs = st.tabs(tab_labels)

for tab, label in zip(tabs, tab_labels):
    with tab:
        st.markdown(
            f"<h2 style='text-align: center;'>{label}</h2>",
            unsafe_allow_html=True,
        )
