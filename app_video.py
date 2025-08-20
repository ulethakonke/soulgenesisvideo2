import streamlit as st
import subprocess
import os
import gc
from pathlib import Path
import tempfile
import shutil

# -----------------------------
# Auto-cleanup function
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

# Initialize session state for auto-cleanup
if "compression_count" not in st.session_state:
    st.session_state.compression_count = 0

# Auto-clear every 3 compressions
if st.session_state.compression_count > 0 and st.session_state.compression_count % 3 == 0:
    gc.collect()
    st.session_state.compression_count = 0

# -----------------------------
# App UI
# -----------------------------
st.set_page_config(page_title="🎥 SoulGenesis Video Compressor", layout="centered")

st.markdown(
    """
    # 🎥 SoulGenesis Video Compressor  
    **Professional FFmpeg-powered compression for maximum file size reduction.**  
    """
)

# Check if FFmpeg is available
def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

if not check_ffmpeg():
    st.error("❌ FFmpeg not found! Please make sure packages.txt includes 'ffmpeg'")
    st.info("💡 Create a packages.txt file with 'ffmpeg' and redeploy your app")
    st.stop()

st.success("✅ FFmpeg is ready!")

st.sidebar.header("⚙️ Compression Settings")

# Preset-based settings for easier use
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

# Advanced settings in expander
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

# -----------------------------
# File Upload
# -----------------------------
uploaded_file = st.file_uploader("📂 Upload your video", type=["mp4", "mov", "avi", "mkv", "webm"])

if uploaded_file:
    file_size_mb = len(uploaded_file.getvalue()) / 1024 / 1024
    
    # File size warnings
    if file_size_mb > 500:
        st.error(f"⚠️ File too large ({file_size_mb:.1f} MB). Please use files under 500MB.")
        st.stop()
    elif file_size_mb > 200:
        st.warning(f"⚠️ Large file ({file_size_mb:.1f} MB). This will take several minutes to process.")
    elif file_size_mb > 50:
        st.info(f"📁 File size: {file_size_mb:.1f} MB - Processing may take a few minutes.")
    else:
        st.info(f"📁 File size: {file_size_mb:.1f} MB")

    # Create temporary file paths
    input_path = None
    output_path = None

    if st.button("🚀 Compress Video", type="primary"):
        try:
            # Create temporary input file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_in:
                tmp_in.write(uploaded_file.read())
                input_path = tmp_in.name

            # Create temporary output file
            output_path = str(Path(tempfile.gettempdir()) / f"compressed_{Path(uploaded_file.name).stem}.mp4")

            # FFmpeg command with error handling
            command = [
                "ffmpeg", "-y",  # Overwrite output file
                "-i", input_path,
                "-c:v", "libx265",        # H.265 codec for best compression
                "-crf", str(crf),         # Quality setting
                "-preset", preset,        # Compression speed
                "-c:a", "aac",           # Audio codec
                "-b:a", audio_bitrate,   # Audio bitrate
                "-movflags", "+faststart", # Web optimization
                "-loglevel", "error",     # Reduce log spam
                output_path
            ]

            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("🔄 Compressing video... This may take several minutes."):
                status_text.text("Processing with FFmpeg...")
                progress_bar.progress(30)
                
                # Run FFmpeg
                result = subprocess.run(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                
                progress_bar.progress(80)
                
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
                
                progress_bar.progress(100)
                status_text.text("Compression complete!")

            st.success("✅ Compression complete!")
            
            # Get file sizes and show results
            original_size = file_size_mb
            compressed_size = os.path.getsize(output_path) / 1024 / 1024
            compression_ratio = (1 - compressed_size/original_size) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Size", f"{original_size:.1f} MB")
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
                file_name=f"compressed_{uploaded_file.name}",
                mime="video/mp4"
            )
            
            # Update counter and cleanup
            st.session_state.compression_count += 1
            
            # Immediate cleanup
            cleanup_temp_files(input_path, output_path)
            del compressed_data

        except subprocess.TimeoutExpired:
            st.error("⏱️ Compression timed out. Try a smaller file or lower quality setting.")
            cleanup_temp_files(input_path, output_path)
            
        except subprocess.CalledProcessError as e:
            st.error(f"❌ FFmpeg error: {e.stderr}")
            st.info("💡 Try different settings or a different video format.")
            cleanup_temp_files(input_path, output_path)
            
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            cleanup_temp_files(input_path, output_path)

# Information section
with st.expander("💡 Compression Guide"):
    st.markdown("""
    **Compression Levels:**
    - **Ultra**: Maximum compression (CRF 32) - smallest files, good for previews/sharing
    - **High**: High compression (CRF 28) - great balance of size and quality  
    - **Medium**: Moderate compression (CRF 25) - good quality retention
    - **Low**: Light compression (CRF 22) - minimal quality loss
    
    **File Size Expectations:**
    - **Ultra**: 70-85% smaller (9.7MB → 1.5-3MB)
    - **High**: 60-75% smaller (9.7MB → 2.5-4MB)
    - **Medium**: 40-60% smaller (9.7MB → 4-6MB)
    - **Low**: 20-40% smaller (9.7MB → 6-8MB)
    
    **Tips:**
    - H.265 codec provides best compression
    - Processing time increases with slower presets
    - Audio quality has minimal impact on file size
    """)

st.markdown("---")
st.markdown("**SoulGenesis Video Compressor** - Professional FFmpeg-powered compression")

# Show session info
if st.session_state.compression_count > 0:
    st.caption(f"Compressions this session: {st.session_state.compression_count} | Auto-cleanup every 3 operations")