import streamlit as st
import subprocess
import os
from pathlib import Path
import tempfile

# -----------------------------
# App UI
# -----------------------------
st.set_page_config(page_title="🎥 SoulGenesis Video Compressor", layout="centered")

st.markdown(
    """
    # 🎥 SoulGenesis Video Compressor  
    **Military-grade offline compression, built for smooth playback and efficiency.**  
    """
)

st.sidebar.header("⚙️ Compression Settings")
crf = st.sidebar.slider("Quality (CRF)", 18, 35, 28, help="Lower = better quality, larger file. Higher = smaller file.")
preset = st.sidebar.selectbox(
    "Encoding Speed Preset",
    ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
    index=3,
    help="Slower presets = better compression efficiency, but slower speed."
)

audio_bitrate = st.sidebar.selectbox("Audio Bitrate", ["64k", "96k", "128k", "192k", "256k"], index=2)

# -----------------------------
# File Upload
# -----------------------------
uploaded_file = st.file_uploader("📂 Upload your video", type=["mp4", "mov", "avi", "mkv"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_in:
        tmp_in.write(uploaded_file.read())
        input_path = tmp_in.name

    # Output path
    output_path = str(Path(tempfile.gettempdir()) / f"compressed_{Path(uploaded_file.name).stem}.mp4")

    if st.button("🚀 Compress Video"):
        try:
            command = [
                "ffmpeg", "-i", input_path,
                "-vcodec", "libx265", "-crf", str(crf),
                "-preset", preset,
                "-acodec", "aac", "-b:a", audio_bitrate,
                "-y", output_path
            ]
            st.info("⏳ Compressing... Please wait, this may take a while depending on video size.")
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            st.success("✅ Compression complete!")
            with open(output_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Compressed Video",
                    data=f,
                    file_name=f"compressed_{uploaded_file.name}",
                    mime="video/mp4"
                )

        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error during compression: {e}")

