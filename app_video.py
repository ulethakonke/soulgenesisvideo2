import io
import os
import tempfile
from pathlib import Path

import streamlit as st

from compress_video import (
    compress_video_ffmpeg,
    package_as_genesisvid,
    unpack_genesisvid,
    make_unique_name,
)

st.set_page_config(page_title="SoulGenesis Video", page_icon="🎥", layout="centered")
st.title("🎥 SoulGenesis Video – Offline Compression & Reconstruction")

st.caption(
    "Uses local **ffmpeg** (H.265 + CRF + AAC). No cloud. Keep audio. Smooth motion. Optional “.genesisvid” packaging."
)

with st.expander("Install once (offline)", expanded=False):
    st.markdown(
        """
**ffmpeg required**  
- **macOS**: `brew install ffmpeg`  
- **Windows**: `choco install ffmpeg` (or download from ffmpeg.org and add to PATH)  
- **Linux (Debian/Ubuntu)**: `sudo apt-get install ffmpeg`  

**Python deps**  
`pip install streamlit`
"""
    )

tab1, tab2 = st.tabs(["Compress ➜ .mp4 / .genesisvid", "Reconstruct from .genesisvid"])

with tab1:
    st.subheader("Compress a video")
    up = st.file_uploader("Upload MP4/MOV/M4V", type=["mp4", "mov", "m4v", "mkv"], accept_multiple_files=False)

    colA, colB = st.columns(2)
    with colA:
        crf = st.slider("Quality (CRF)", 18, 36, 28, help="Lower = better quality (and larger). 26–30 is a good range.")
        preset = st.selectbox(
            "Speed/Size Preset",
            ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            index=5,
            help="Slower gives smaller files.",
        )
    with colB:
        fps = st.number_input("Target FPS (0 = keep source)", min_value=0, max_value=120, value=0, step=1)
        max_res = st.selectbox("Max Resolution (long side)", ["Keep source", 480, 720, 1080, 1440, 2160], index=2)

    wrap_genesis = st.checkbox("Also package as .genesisvid", value=True)

    if st.button("Compress"):
        if not up:
            st.warning("Upload a video first.")
        else:
            try:
                # Save uploaded file to a temp path
                suffix = Path(up.name).suffix or ".mp4"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
                    tmp_in.write(up.getbuffer())
                    in_path = Path(tmp_in.name)

                # Build output names
                stem = Path(up.name).stem
                fps_opt = None if fps == 0 else int(fps)
                res_opt = None if max_res == "Keep source" else int(max_res)

                out_name_mp4 = make_unique_name(stem, crf, fps_opt, res_opt, "mp4")
                out_name_gen = make_unique_name(stem, crf, fps_opt, res_opt, "genesisvid")

                tmp_out_mp4 = Path(tempfile.gettempdir()) / out_name_mp4
                # Compress
                compressed_mp4 = compress_video_ffmpeg(
                    input_path=in_path,
                    output_path=tmp_out_mp4,
                    crf=crf,
                    preset=preset,
                    target_fps=fps_opt,
                    max_resolution=res_opt,
                )

                # Show stats
                in_size = Path(in_path).stat().st_size
                out_size = Path(compressed_mp4).stat().st_size
                reduction = (1 - out_size / max(in_size, 1)) * 100

                st.success(f"Done. Size: {in_size/1e6:.2f} MB → {out_size/1e6:.2f} MB ({reduction:.1f}% smaller)")
                st.video(str(compressed_mp4))

                with open(compressed_mp4, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download MP4 ({out_name_mp4})",
                        data=f.read(),
                        file_name=out_name_mp4,
                        mime="video/mp4",
                    )

                if wrap_genesis:
                    tmp_out_gen = Path(tempfile.gettempdir()) / out_name_gen
                    gen_path, meta = package_as_genesisvid(
                        mp4_path=compressed_mp4,
                        genesis_path=tmp_out_gen,
                        orig_name=up.name,
                        codec="libx265",
                        crf=crf,
                        preset=preset,
                        target_fps=fps_opt,
                        max_resolution=res_opt,
                    )
                    with open(gen_path, "rb") as gf:
                        st.download_button(
                            label=f"⬇️ Download .genesisvid ({out_name_gen})",
                            data=gf.read(),
                            file_name=out_name_gen,
                            mime="application/octet-stream",
                        )

                # Clean input temp (keep outputs until app restarts)
                try:
                    in_path.unlink(missing_ok=True)
                except Exception:
                    pass

            except Exception as e:
                st.error(f"Error during compression: {e}")

with tab2:
    st.subheader("Reconstruct from .genesisvid")
    gen = st.file_uploader("Upload .genesisvid", type=["genesisvid"], accept_multiple_files=False)

    if st.button("Reconstruct"):
        if not gen:
            st.warning("Upload a .genesisvid file first.")
        else:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_gen:
                    tmp_gen.write(gen.getbuffer())
                    gen_path = Path(tmp_gen.name)

                # Output mp4 path
                out_mp4 = Path(tempfile.gettempdir()) / (Path(gen.name).stem + "_recon.mp4")
                recon_mp4, meta = unpack_genesisvid(genesis_path=gen_path, out_mp4_path=out_mp4)

                st.success("Reconstructed MP4 from .genesisvid")
                st.json(meta)
                st.video(str(recon_mp4))

                with open(recon_mp4, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Reconstructed MP4 ({Path(recon_mp4).name})",
                        data=f.read(),
                        file_name=Path(recon_mp4).name,
                        mime="video/mp4",
                    )

            except Exception as e:
                st.error(f"Error during reconstruction: {e}")
