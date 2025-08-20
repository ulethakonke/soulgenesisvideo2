import streamlit as st
from pathlib import Path
from compress_video import compress_video, decompress_video

# Set page config
st.set_page_config(
    page_title="SoulGenesis Video Compressor",
    page_icon="🎥",
    layout="centered"
)

# Styling
st.markdown(
    """
    <style>
    .main {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stButton>button {
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        color: black;
        border-radius: 12px;
        padding: 0.6em 1.2em;
        font-weight: bold;
        border: none;
    }
    .stDownloadButton>button {
        background: linear-gradient(90deg, #FF8A00 0%, #E52E71 100%);
        color: white;
        border-radius: 12px;
        padding: 0.6em 1.2em;
        font-weight: bold;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎥 SoulGenesis Video Compressor")
st.caption("Military-grade offline compression, built for smooth playback and efficiency.")

# Increase upload size to 2 GB
st.file_uploader.__defaults__ = (["mp4", "mov", "avi", "mkv"], "Upload video...", True, "file", 2 * 1024 * 1024 * 1024)

# Tabs
tab1, tab2 = st.tabs(["📦 Compress Video", "🔓 Decompress Video"])

# ============ Compression ============
with tab1:
    st.subheader("📦 Compress to .genesisvid.mp4")

    uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"], key="compress")

    crf = st.slider("🎚️ Compression Quality (Lower = Better Quality, Larger File)", 18, 35, 28)
    preset = st.selectbox("⚡ Encoding Speed / Compression Trade-off",
                          ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                          index=5)

    if uploaded_file and st.button("🚀 Compress Video"):
        in_path = Path(uploaded_file.name)
        with open(in_path, "wb") as f:
            f.write(uploaded_file.read())

        out_path = Path(in_path.stem + "_compressed.genesisvid.mp4")

        with st.spinner("Compressing... please wait ⏳"):
            compress_video(in_path, out_path, crf=crf, preset=preset)

        if out_path.exists():
            st.success(f"✅ Compression complete: {out_path.name}")
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Download Compressed Video", f, file_name=out_path.name)

# ============ Decompression ============
with tab2:
    st.subheader("🔓 Decompress .genesisvid.mp4 back to playable MP4")

    uploaded_file = st.file_uploader("Upload .genesisvid.mp4", type=["mp4"], key="decompress")

    if uploaded_file and st.button("🔓 Decompress Video"):
        in_path = Path(uploaded_file.name)
        with open(in_path, "wb") as f:
            f.write(uploaded_file.read())

        out_path = Path(in_path.stem.replace("_compressed", "") + "_decompressed.mp4")

        with st.spinner("Decompressing... please wait ⏳"):
            decompress_video(in_path, out_path)

        if out_path.exists():
            st.success(f"✅ Decompression complete: {out_path.name}")
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Download Decompressed Video", f, file_name=out_path.name)
