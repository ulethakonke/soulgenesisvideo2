import streamlit as st
import tempfile
import subprocess
import shutil
import time
from pathlib import Path

# =========================
# App configuration
# =========================
st.set_page_config(page_title="SoulGenesis Video Compressor", page_icon="🎥", layout="centered")

# 2GB upload limit (in MB)
st.set_option("server.maxUploadSize", 2048)     # 2 GB
st.set_option("server.maxMessageSize", 2048)    # 2 GB

# =========================
# Minimal styling
# =========================
st.markdown(
    """
    <style>
      .sg-header {text-align:center; margin-top: 0.5rem; margin-bottom: 1.25rem;}
      .sg-title {font-size: 2.0rem; font-weight: 800; letter-spacing: .3px;}
      .sg-sub {color: #6b7280;}
      .sg-card {border: 1px solid #e5e7eb; border-radius: 16px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #ffffffcc;}
      .sg-h2 {font-size: 1.05rem; font-weight: 700; margin: 0 0 .75rem 0;}
      .sg-help {color: #6b7280; font-size: .9rem; margin-top: .25rem;}
      .sg-ok {background: #10b98122; border: 1px solid #10b98155; padding: .5rem .75rem; border-radius: 10px;}
      .sg-warn {background: #f59e0b22; border: 1px solid #f59e0b55; padding: .5rem .75rem; border-radius: 10px;}
      .block-container {padding-top: 1.2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sg-header">
      <div class="sg-title">🎥 SoulGenesis Video Compressor</div>
      <div class="sg-sub">Offline, FFmpeg-powered compression with smooth playback and simple restore.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# Utilities
# =========================
def ensure_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None

def save_uploaded_to_temp(upload, suffix: str) -> Path:
    """Save a Streamlit UploadedFile to a NamedTemporaryFile and return Path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload.read())
        return Path(tmp.name)

def unique_out_name(stem: str, ext: str) -> str:
    """Generate a unique filename with timestamp to avoid 'copy' issues on macOS."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{stem}_{ts}{ext}"

def run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    """Run ffmpeg and return (exit_code, combined_stdout_stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
        return proc.returncode, proc.stdout
    except Exception as e:
        return 1, f"FFmpeg execution failed: {e}"

# =========================
# Compression (to .genesisvid)
# =========================
with st.container():
    st.markdown('<div class="sg-card">', unsafe_allow_html=True)
    st.markdown('<div class="sg-h2">Compress a video → <code>.genesisvid</code></div>', unsafe_allow_html=True)

    if not ensure_ffmpeg():
        st.error("FFmpeg is not installed or not on your PATH. Install it, then restart the app.")
        st.markdown('<div class="sg-help">macOS quick path: install from Evermeet or Homebrew. Verify in Terminal: <code>ffmpeg -version</code>.</div>', unsafe_allow_html=True)

    uploaded_vid = st.file_uploader(
        "Upload video...",
        type=["mp4", "mov", "avi", "mkv"],
        key="vid_upload",
        help="Max 2 GB. Common formats supported."
    )

    # Encoding controls
    col1, col2, col3 = st.columns(3)
    with col1:
        crf = st.slider("Quality (CRF)", min_value=18, max_value=35, value=24, help="Lower = better quality, larger file. 23–26 is a good range.")
    with col2:
        preset = st.selectbox("Speed/Preset", ["ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow"], index=5, help="Slower = better compression (smaller file), but more CPU time.")
    with col3:
        audio_bitrate = st.selectbox("Audio bitrate", ["64k", "96k", "128k", "160k", "192k"], index=2)

    keep_fps = st.checkbox("Preserve original FPS (recommended)", value=True, help="Leave ON for smooth motion. Turn OFF only if you plan to force a lower FPS.")
    force_fps = None
    if not keep_fps:
        force_fps = st.number_input("Force FPS (e.g. 24 or 30)", min_value=1, max_value=120, value=24)

    if uploaded_vid and ensure_ffmpeg():
        # Save input to temp
        in_suffix = Path(uploaded_vid.name).suffix or ".mp4"
        in_tmp_path = save_uploaded_to_temp(uploaded_vid, suffix=in_suffix)

        stem = Path(uploaded_vid.name).stem
        out_name = unique_out_name(stem, ".genesisvid")
        out_tmp_path = Path(tempfile.gettempdir()) / out_name

        # We encode to H.265/AAC inside MP4, then simply write the MP4 bytes with .genesisvid extension.
        # That keeps "decompression" as a simple rename back to MP4.
        mp4_tmp = Path(tempfile.gettempdir()) / unique_out_name(stem, ".mp4")

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(in_tmp_path),

            # Video: HEVC (H.265) CRF + preset
            "-c:v", "libx265",
            "-crf", str(crf),
            "-preset", preset,

            # Keep VFR timing if present; don't force CFR unless user wants a specific fps
            "-vsync", "vfr",
            "-fps_mode", "passthrough",
        ]

        if force_fps is not None:
            ffmpeg_cmd += ["-r", str(force_fps)]  # force CFR

        # Audio: AAC at chosen bitrate; use aac encoder for broad compatibility
        ffmpeg_cmd += [
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-movflags", "+faststart",
            str(mp4_tmp),
        ]

        st.button("Compress", key="compress_btn", help="Click to start compression.")

        if st.session_state.get("compress_btn"):
            with st.status("Compressing… This can take a while for larger files.", expanded=True) as status:
                st.write(f"Running FFmpeg with CRF {crf}, preset {preset}, audio {audio_bitrate}…")
                code, log = run_ffmpeg(ffmpeg_cmd)
                if code != 0:
                    status.update(label="Compression failed", state="error")
                    st.error("Error during compression.")
                    st.code(log, language="bash")
                else:
                    # Write the .genesisvid as a byte-identical copy of the MP4
                    try:
                        out_tmp_path.write_bytes(mp4_tmp.read_bytes())
                        status.update(label="Compression complete", state="complete")
                        st.success("Compressed successfully!")
                        st.markdown(f'<div class="sg-ok">Output created: <code>{out_tmp_path.name}</code></div>', unsafe_allow_html=True)
                        with open(out_tmp_path, "rb") as f:
                            st.download_button(
                                "⬇️ Download .genesisvid",
                                data=f,
                                file_name=out_tmp_path.name,
                                mime="application/octet-stream",
                            )
                    except Exception as e:
                        status.update(label="Write failed", state="error")
                        st.error(f"Failed to finalize .genesisvid: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Decompression (from .genesisvid back to MP4)
# =========================
with st.container():
    st.markdown('<div class="sg-card">', unsafe_allow_html=True)
    st.markdown('<div class="sg-h2">Reconstruct video from <code>.genesisvid</code> → MP4</div>', unsafe_allow_html=True)

    uploaded_gen = st.file_uploader(
        "Upload .genesisvid",
        type=["genesisvid"],
        key="gen_upload",
        help="This simply restores the MP4 container and filename (no cloud needed)."
    )

    if uploaded_gen:
        in_tmp_path = save_uploaded_to_temp(uploaded_gen, suffix=".genesisvid")
        stem = Path(uploaded_gen.name).stem
        # If original was something like name_20240101_010101.genesisvid, still produce a clean mp4 name:
        clean_stem = stem.replace(".genesis", "").replace(".copy", "")
        out_name = unique_out_name(clean_stem, ".mp4")
        out_tmp_path = Path(tempfile.gettempdir()) / out_name

        # "Decompression": copy bytes and set .mp4 extension
        try:
            out_tmp_path.write_bytes(Path(in_tmp_path).read_bytes())
            st.success("Reconstruction complete (MP4 restored).")
            st.markdown(f'<div class="sg-ok">Output created: <code>{out_tmp_path.name}</code></div>', unsafe_allow_html=True)
            with open(out_tmp_path, "rb") as f:
                st.download_button(
                    "⬇️ Download reconstructed MP4",
                    data=f,
                    file_name=out_tmp_path.name,
                    mime="video/mp4",
                )
        except Exception as e:
            st.error(f"Error during reconstruction: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Tips / Notes
# =========================
with st.container():
    st.markdown('<div class="sg-card">', unsafe_allow_html=True)
    st.markdown('<div class="sg-h2">Notes</div>', unsafe_allow_html=True)
    st.markdown(
        """
        - Uses **FFmpeg** locally (no servers). Make sure `ffmpeg -version` works in your Terminal.
        - H.265 (HEVC) with **CRF** gives strong compression while keeping motion smooth.
        - Keep **“Preserve original FPS”** ON for natural playback. Only force FPS if you know you want a specific frame rate.
        - The **.genesisvid** file is an MP4 under the hood with a custom extension for your workflow; “decompression” restores it to `.mp4`.
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
