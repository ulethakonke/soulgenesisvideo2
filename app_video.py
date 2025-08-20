import streamlit as st
import tempfile
from pathlib import Path
from PIL import Image
import subprocess
import os
import json
import zlib
import numpy as np
import gc

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="SoulGenesis - Media Compression",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Utility Functions
# -----------------------------
def cleanup_temp_files(*file_paths):
    """Clean up temporary files and clear memory"""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except:
            pass
    gc.collect()

def check_ffmpeg():
    """Check if FFmpeg is available on the system"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

# -----------------------------
# Image Compression Functions
# -----------------------------
def compress_image(input_path, output_path, quality=85):
    """Compress image using adaptive method (JPEG+Zlib or Palette+Zlib)"""
    img = Image.open(input_path).convert("RGB")
    
    if img.size[0] * img.size[1] > 500000:
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            img.save(tmp.name, quality=quality, optimize=True)
            tmp.seek(0)
            compressed_data = zlib.compress(tmp.read(), level=9)
            method = "JPEG+Zlib"
    else:
        img_p = img.convert("P", palette=Image.ADAPTIVE, colors=256)
        palette = img_p.getpalette()[:768]
        arr = np.array(img_p)
        data = {
            "size": img.size,
            "palette": [palette[i:i+3] for i in range(0, len(palette), 3)],
            "pixels": arr.flatten().tolist()
        }
        compressed_data = zlib.compress(json.dumps(data).encode("utf-8"), level=9)
        method = "Palette+Zlib"

    with open(output_path, "wb") as f:
        f.write(compressed_data)
    
    return method

def decompress_image(input_path, output_path):
    """Decompress .genesis file back to image"""
    with open(input_path, "rb") as f:
        data = zlib.decompress(f.read())
    
    try:
        with open(output_path, "wb") as f:
            f.write(data)
        Image.open(output_path).verify()
    except:
        data = json.loads(data.decode("utf-8"))
        size = tuple(data["size"])
        palette = data["palette"]
        pixels = np.array(data["pixels"], dtype=np.uint8).reshape(size[1], size[0])
        img_p = Image.fromarray(pixels, mode="P")
        img_p.putpalette([x for rgb in palette for x in rgb])
        img_rgb = img_p.convert("RGB")
        img_rgb.save(output_path)

# -----------------------------
# Video Compression Functions
# -----------------------------
def compress_video(in_path, out_path, crf=28, preset="medium", audio_bitrate="128k"):
    """Compress video using FFmpeg with H.265 codec"""
    in_path = str(Path(in_path))
    out_path = str(Path(out_path))

    cmd = [
        "ffmpeg", "-y",
        "-i", in_path,
        "-c:v", "libx265",
        "-preset", preset,
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-movflags", "+faststart",
        "-loglevel", "error",
        out_path
    ]
    subprocess.run(cmd, check=True, timeout=600)

def decompress_video(in_path, out_path):
    """Decompress video by re-encoding to H.264"""
    in_path = str(Path(in_path))
    out_path = str(Path(out_path))

    cmd = [
        "ffmpeg", "-y",
        "-i", in_path,
        "-c:v", "libx264",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-loglevel", "error",
        out_path
    ]
    subprocess.run(cmd, check=True, timeout=600)

# -----------------------------
# UI Components
# -----------------------------
def sidebar_controls():
    """Render sidebar controls based on selected mode"""
    st.sidebar.title("⚙️ Settings")
    
    mode = st.sidebar.radio(
        "Select Compression Mode",
        ["Image Compression", "Video Compression"],
        help="Choose whether to work with images or videos"
    )
    
    if mode == "Image Compression":
        quality = st.sidebar.slider(
            "Compression Quality", 
            50, 100, 85,
            help="Higher values give better quality but larger files"
        )
        return mode, quality
    
    else:  # Video Compression
        # Preset-based settings
        compression_preset = st.sidebar.selectbox(
            "Compression Level",
            ["Ultra (Smallest File)", "High", "Medium", "Low (Best Quality)"],
            index=1,
            help="Choose your compression level"
        )
        
        # Map presets to CRF values
        preset_map = {
            "Ultra (Smallest File)": {"crf": 32, "preset": "fast", "description": "70-85% size reduction"},
            "High": {"crf": 28, "preset": "medium", "description": "60-75% size reduction"}, 
            "Medium": {"crf": 25, "preset": "medium", "description": "40-60% size reduction"},
            "Low (Best Quality)": {"crf": 22, "preset": "slow", "description": "20-40% size reduction"}
        }
        
        selected_preset = preset_map[compression_preset]
        st.sidebar.info(f"📊 Expected: {selected_preset['description']}")
        
        # Advanced settings
        with st.sidebar.expander("🔧 Advanced Settings"):
            custom_crf = st.slider("Custom Quality (CRF)", 18, 35, selected_preset["crf"], 
                                  help="Lower = better quality, larger file")
            
            custom_preset = st.selectbox(
                "Encoding Speed",
                ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"],
                index=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"].index(selected_preset["preset"])
            )
            
            audio_bitrate = st.selectbox("Audio Quality", ["64k", "96k", "128k", "192k"], index=2)
            
            use_custom = st.checkbox("Use custom settings", value=False)
        
        # Use custom settings if enabled
        if use_custom:
            crf = custom_crf
            preset = custom_preset
        else:
            crf = selected_preset["crf"]
            preset = selected_preset["preset"]
            
        return mode, {"crf": crf, "preset": preset, "audio_bitrate": audio_bitrate}

# -----------------------------
# Main Application
# -----------------------------
def main():
    # Initialize session state
    if "compression_count" not in st.session_state:
        st.session_state.compression_count = 0
    
    # Header
    st.title("✨ SoulGenesis - Ultimate Media Compression")
    st.markdown("Compress and reconstruct images and videos with advanced algorithms - **100% offline processing**")
    
    # Check for FFmpeg (warn only for video operations)
    ffmpeg_available = check_ffmpeg()
    
    # Sidebar
    mode, settings = sidebar_controls()
    
    # Main content area
    tab1, tab2 = st.tabs(["📤 Compress", "📥 Decompress"])
    
    with tab1:
        st.header("Compress Media Files")
        
        if mode == "Image Compression":
            img_file = st.file_uploader("Choose an image to compress", 
                                       type=["png", "jpg", "jpeg"], 
                                       key="img_compress")
            
            if img_file:
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img_file, caption="Original Image", use_container_width=True)
                    file_size = len(img_file.getvalue()) / 1024
                    st.metric("Original Size", f"{file_size:.1f} KB")
                
                if st.button("🚀 Compress Image", type="primary"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(img_file.name).suffix) as tmp_in:
                        tmp_in.write(img_file.read())
                        tmp_in_path = tmp_in.name
                    
                    out_path = Path(tempfile.gettempdir()) / (Path(img_file.name).stem + ".genesis")
                    
                    with st.spinner("Compressing image..."):
                        method = compress_image(tmp_in_path, out_path, settings)
                    
                    compressed_size = os.path.getsize(out_path) / 1024
                    compression_ratio = (1 - compressed_size/file_size) * 100
                    
                    with col2:
                        st.success(f"Compressed using {method}")
                        st.metric("Compressed Size", f"{compressed_size:.1f} KB")
                        st.metric("Size Reduction", f"{compression_ratio:.1f}%")
                    
                    with open(out_path, "rb") as f:
                        st.download_button("⬇️ Download .genesis file", f, 
                                          file_name=Path(out_path).name,
                                          key="dl_genesis")
                    
                    cleanup_temp_files(tmp_in_path, out_path)
                    st.session_state.compression_count += 1
        
        else:  # Video Compression
            if not ffmpeg_available:
                st.warning("⚠️ FFmpeg not found! Video compression requires FFmpeg to be installed.")
                st.info("On Ubuntu/Debian: `sudo apt install ffmpeg`")
                st.info("On macOS: `brew install ffmpeg`")
                st.info("On Windows: Download from https://ffmpeg.org/")
            
            video_file = st.file_uploader("Choose a video to compress", 
                                         type=["mp4", "mov", "avi", "mkv", "webm"], 
                                         key="vid_compress")
            
            if video_file and ffmpeg_available:
                file_size_mb = len(video_file.getvalue()) / 1024 / 1024
                
                # File size warnings
                if file_size_mb > 500:
                    st.error(f"⚠️ File too large ({file_size_mb:.1f} MB). Please use files under 500MB.")
                else:
                    if file_size_mb > 200:
                        st.warning(f"⚠️ Large file ({file_size_mb:.1f} MB). This will take several minutes to process.")
                    elif file_size_mb > 50:
                        st.info(f"📁 File size: {file_size_mb:.1f} MB - Processing may take a few minutes.")
                    else:
                        st.info(f"📁 File size: {file_size_mb:.1f} MB")
                    
                    if st.button("🚀 Compress Video", type="primary"):
                        input_path = None
                        output_path = None
                        
                        try:
                            # Create temporary input file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video_file.name).suffix) as tmp_in:
                                tmp_in.write(video_file.read())
                                input_path = tmp_in.name

                            # Create temporary output file
                            output_path = str(Path(tempfile.gettempdir()) / f"compressed_{Path(video_file.name).stem}.mp4")
                            
                            # Show progress
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            with st.spinner("🔄 Compressing video... This may take several minutes."):
                                status_text.text("Processing with FFmpeg...")
                                progress_bar.progress(30)
                                
                                # Compress video
                                compress_video(input_path, output_path, 
                                              settings["crf"], 
                                              settings["preset"], 
                                              settings["audio_bitrate"])
                                
                                progress_bar.progress(80)
                                progress_bar.progress(100)
                                status_text.text("Compression complete!")

                            st.success("✅ Compression complete!")
                            
                            # Get file sizes and show results
                            compressed_size = os.path.getsize(output_path) / 1024 / 1024
                            compression_ratio = (1 - compressed_size/file_size_mb) * 100
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Original Size", f"{file_size_mb:.1f} MB")
                            with col2:
                                st.metric("Compressed Size", f"{compressed_size:.1f} MB") 
                            with col3:
                                st.metric("Size Reduction", f"{compression_ratio:.1f}%")

                            # Success message based on compression ratio
                            if compression_ratio > 70:
                                st.success(f"🎉 Excellent compression! File reduced by {compression_ratio:.1f}%")
                            elif compression_ratio > 50:
                                st.success(f"✅ Good compression! File reduced by {compression_ratio:.1f}%")
                            elif compression_ratio > 25:
                                st.info(f"📊 Moderate compression: {compression_ratio:.1f}% reduction")
                            else:
                                st.warning(f"⚠️ Limited compression: {compression_ratio:.1f}% reduction. Try Ultra setting for smaller files.")

                            # Download button
                            with open(output_path, "rb") as f:
                                compressed_data = f.read()
                                
                            st.download_button(
                                label="⬇️ Download Compressed Video",
                                data=compressed_data,
                                file_name=f"compressed_{video_file.name}",
                                mime="video/mp4"
                            )
                            
                            # Update counter and cleanup
                            st.session_state.compression_count += 1
                            cleanup_temp_files(input_path, output_path)
                            
                        except subprocess.TimeoutExpired:
                            st.error("⏱️ Compression timed out. Try a smaller file or lower quality setting.")
                            cleanup_temp_files(input_path, output_path)
                            
                        except subprocess.CalledProcessError as e:
                            st.error(f"❌ FFmpeg error: {str(e)}")
                            st.info("💡 Try different settings or a different video format.")
                            cleanup_temp_files(input_path, output_path)
                            
                        except Exception as e:
                            st.error(f"❌ Unexpected error: {str(e)}")
                            cleanup_temp_files(input_path, output_path)
    
    with tab2:
        st.header("Decompress Media Files")
        
        if mode == "Image Compression":
            genesis_file = st.file_uploader("Choose a .genesis file to reconstruct", 
                                           type=["genesis"], 
                                           key="genesis_decompress")
            
            if genesis_file:
                if st.button("🔍 Reconstruct Image", type="primary"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".genesis") as tmp_in:
                        tmp_in.write(genesis_file.read())
                        tmp_in_path = tmp_in.name
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_out:
                        tmp_out_path = tmp_out.name
                    
                    with st.spinner("Reconstructing image..."):
                        decompress_image(tmp_in_path, tmp_out_path)
                    
                    img = Image.open(tmp_out_path)
                    st.image(img, caption="Reconstructed Image", use_container_width=True)
                    
                    with open(tmp_out_path, "rb") as f:
                        st.download_button("⬇️ Download Reconstructed Image", f, 
                                          file_name="reconstructed.png",
                                          key="dl_reconstructed")
                    
                    cleanup_temp_files(tmp_in_path, tmp_out_path)
        
        else:  # Video Decompression
            if not ffmpeg_available:
                st.warning("⚠️ FFmpeg not found! Video decompression requires FFmpeg to be installed.")
            
            compressed_vid = st.file_uploader("Choose a compressed video to decompress", 
                                             type=["mp4", "mov"], 
                                             key="vid_decompress")
            
            if compressed_vid and ffmpeg_available:
                if st.button("🔍 Decompress Video", type="primary"):
                    input_path = None
                    output_path = None
                    
                    try:
                        # Create temporary input file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(compressed_vid.name).suffix) as tmp_in:
                            tmp_in.write(compressed_vid.read())
                            input_path = tmp_in.name

                        # Create temporary output file
                        output_path = str(Path(tempfile.gettempdir()) / f"decompressed_{Path(compressed_vid.name).stem}.mp4")
                        
                        with st.spinner("Decompressing video..."):
                            decompress_video(input_path, output_path)
                        
                        st.success("✅ Decompression complete!")
                        
                        # Download button
                        with open(output_path, "rb") as f:
                            decompressed_data = f.read()
                            
                        st.download_button(
                            label="⬇️ Download Decompressed Video",
                            data=decompressed_data,
                            file_name=f"decompressed_{compressed_vid.name}",
                            mime="video/mp4"
                        )
                        
                        cleanup_temp_files(input_path, output_path)
                        
                    except subprocess.TimeoutExpired:
                        st.error("⏱️ Decompression timed out. The file might be corrupted.")
                        cleanup_temp_files(input_path, output_path)
                        
                    except Exception as e:
                        st.error(f"❌ Error during decompression: {str(e)}")
                        cleanup_temp_files(input_path, output_path)
    
    # Information section
    with st.expander("💡 Usage Guide"):
        if mode == "Image Compression":
            st.markdown("""
            **Image Compression Guide:**
            - **Compression Quality**: Higher values preserve more detail but create larger files
            - **Smart Algorithm**: Automatically chooses the best method for your image
            - **Genesis Format**: Proprietary compressed format with excellent compression ratios
            
            **Supported Formats:** JPEG, PNG → .genesis
            """)
        else:
            st.markdown("""
            **Video Compression Guide:**
            - **Ultra**: Maximum compression (CRF 32) - smallest files, good for previews/sharing
            - **High**: High compression (CRF 28) - great balance of size and quality  
            - **Medium**: Moderate compression (CRF 25) - good quality retention
            - **Low**: Light compression (CRF 22) - minimal quality loss
            
            **Tips:**
            - H.265 codec provides best compression
            - Processing time increases with slower presets
            - Audio quality has minimal impact on file size
            
            **Supported Formats:** MP4, MOV, AVI, MKV, WebM → Compressed MP4
            """)
    
    # Footer
    st.markdown("---")
    st.markdown("**SoulGenesis Media Compressor** - Professional FFmpeg-powered compression • 100% Offline Processing")
    
    # Show session info
    if st.session_state.compression_count > 0:
        st.caption(f"Operations this session: {st.session_state.compression_count}")

# -----------------------------
# Run the application
# -----------------------------
if __name__ == "__main__":
    main()