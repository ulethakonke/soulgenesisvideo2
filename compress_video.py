import subprocess
from pathlib import Path

def compress_video(in_path, out_path, crf=28, preset="medium"):
    """
    Compress video using ffmpeg with H.265 (HEVC) codec + AAC audio.
    
    Args:
        in_path (str or Path): Input video file (MP4, MOV, etc.)
        out_path (str or Path): Output compressed file (.genesisvid.mp4)
        crf (int): Constant Rate Factor (lower = better quality, larger file).
                   Typical range: 18 (visually lossless) to 30 (high compression).
        preset (str): Compression speed/efficiency tradeoff.
                      Options: ultrafast, superfast, veryfast, faster,
                               fast, medium, slow, slower, veryslow
    """
    in_path = str(Path(in_path))
    out_path = str(Path(out_path))

    try:
        cmd = [
            "ffmpeg",
            "-i", in_path,
            "-c:v", "libx265",        # H.265 codec
            "-preset", preset,        # Compression speed/efficiency
            "-crf", str(crf),         # Quality setting
            "-c:a", "aac",            # Use AAC audio
            "-b:a", "128k",           # Audio bitrate
            "-movflags", "+faststart", # Optimized for web playback
            out_path
        ]
        subprocess.run(cmd, check=True)
        print(f"✅ Compression complete: {out_path}")
    except Exception as e:
        print(f"❌ Error during compression: {e}")


def decompress_video(in_path, out_path):
    """
    Decompress video by simply re-encoding back to H.264 (wider compatibility).
    """
    in_path = str(Path(in_path))
    out_path = str(Path(out_path))

    try:
        cmd = [
            "ffmpeg",
            "-i", in_path,
            "-c:v", "libx264",   # Standard H.264 for playback anywhere
            "-crf", "18",        # High quality for restore
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path
        ]
        subprocess.run(cmd, check=True)
        print(f"✅ Decompression complete: {out_path}")
    except Exception as e:
        print(f"❌ Error during decompression: {e}")
