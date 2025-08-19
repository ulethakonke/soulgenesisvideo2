import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

MAGIC = b"GENV1"  # .genesisvid magic bytes


def _run_ffmpeg(cmd):
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "ffmpeg failed. Ensure ffmpeg is installed and on PATH."
        ) from e


def compress_video_ffmpeg(
    input_path,
    output_path,
    crf=28,
    preset="medium",
    target_fps=None,
    max_resolution=None,
    audio_bitrate="128k",
):
    """
    Compress video using H.265 (HEVC) + CRF + AAC audio.
    - crf: lower = better quality, larger file. Typical 18–32. Start with 26–28.
    - preset: "ultrafast" ... "veryslow" (slower = smaller file).
    - target_fps: e.g., 24; None = keep original FPS (ffmpeg will preserve).
    - max_resolution: e.g., 720 (long side capped). None = keep original.
    - audio_bitrate: e.g., "128k".
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    vf_parts = []
    if max_resolution:
        # Scale long side down to max_resolution, preserve aspect
        vf_parts.append(
            f"scale='if(gt(iw,ih),{max_resolution},-2)':'if(gt(ih,iw),{max_resolution},-2)':force_original_aspect_ratio=decrease"
        )
    if target_fps:
        vf_parts.append(f"fps={int(target_fps)}")

    vf = ",".join(vf_parts) if vf_parts else "null"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        vf,
        "-c:v",
        "libx265",
        "-preset",
        str(preset),
        "-crf",
        str(int(crf)),
        "-c:a",
        "aac",
        "-b:a",
        str(audio_bitrate),
        str(output_path),
    ]
    _run_ffmpeg(cmd)
    return str(output_path)


def _sha1_file(path, chunk=1024 * 1024):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def package_as_genesisvid(
    mp4_path,
    genesis_path,
    orig_name,
    codec="libx265",
    crf=28,
    preset="medium",
    target_fps=None,
    max_resolution=None,
):
    """
    Create a .genesisvid container:
    [5B MAGIC][8B little-endian JSON length][JSON UTF-8][MP4 bytes]
    """
    mp4_path = Path(mp4_path)
    genesis_path = Path(genesis_path)

    meta = {
        "orig_name": orig_name,
        "container_version": "1",
        "codec": codec,
        "crf": int(crf),
        "preset": str(preset),
        "target_fps": int(target_fps) if target_fps else None,
        "max_resolution": int(max_resolution) if max_resolution else None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "compressed_sha1": _sha1_file(mp4_path),
        "compressed_size": mp4_path.stat().st_size,
    }
    meta_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")
    header_len = len(meta_bytes).to_bytes(8, "little")

    with open(mp4_path, "rb") as fin, open(genesis_path, "wb") as fout:
        fout.write(MAGIC)
        fout.write(header_len)
        fout.write(meta_bytes)
        fout.write(fin.read())
    return str(genesis_path), meta


def unpack_genesisvid(genesis_path, out_mp4_path):
    genesis_path = Path(genesis_path)
    out_mp4_path = Path(out_mp4_path)

    with open(genesis_path, "rb") as f:
        magic = f.read(5)
        if magic != MAGIC:
            raise ValueError("Not a .genesisvid file (bad magic bytes).")
        header_len = int.from_bytes(f.read(8), "little")
        meta_bytes = f.read(header_len)
        meta = json.loads(meta_bytes.decode("utf-8"))

        with open(out_mp4_path, "wb") as out:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                out.write(block)

    # Verify hash if present
    try:
        sha = _sha1_file(out_mp4_path)
        if "compressed_sha1" in meta and meta["compressed_sha1"] != sha:
            raise ValueError("Hash mismatch: file may be corrupted.")
    except Exception as _:
        # Leave file for debugging but raise
        raise

    return str(out_mp4_path), meta


def make_unique_name(stem, crf, fps, res, ext):
    parts = [stem, f"crf{int(crf)}"]
    parts.append(f"fps{int(fps)}" if fps else "fpsSRC")
    parts.append(f"r{int(res)}" if res else "rSRC")
    base = "_".join(parts)
    return f"{base}.{ext}"
