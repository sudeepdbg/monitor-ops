"""
VideoForge Studio V2
Professional Video Optimization Platform
Streamlit single-file app
"""
import re
import json
import time
import uuid
import shutil
import subprocess
import zipfile
import base64
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_webrtc import webrtc_streamer, RTCConfiguration
    WEBRTC_AVAILABLE = True
except Exception:
    WEBRTC_AVAILABLE = False

# ============================================================
# Paths
# ============================================================
WORK = Path("work")
IN_DIR = WORK / "inputs"
OUT_DIR = WORK / "outputs"
LOG_DIR = WORK / "logs"
for d in (IN_DIR, OUT_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# Page config + Inter typography + modern light theme
# ============================================================
st.set_page_config(
    page_title="VideoForge Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
https://fonts.googleapis.com
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: linear-gradient(180deg, #f7faff 0%, #eef4fb 100%) !important;
    color: #0f172a !important;
}
[data-testid="stHeader"] { background: rgba(247,250,255,.85) !important; backdrop-filter: blur(10px); }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px; }
* { font-family: 'Inter', -apple-system, sans-serif !important; }
h1, h2, h3, h4 { letter-spacing: -0.02em; color: #0f172a; font-weight: 800; }
.hero {
    background: linear-gradient(135deg, #ffffff 0%, #f0f6ff 100%);
    border: 1px solid #dbeafe;
    border-radius: 24px;
    padding: 26px 30px;
    box-shadow: 0 12px 36px rgba(59,130,246,.10);
    margin-bottom: 22px;
}
.hero h1 { font-size: 2.2rem; margin: 0; font-weight: 900; }
.hero p { color: #475569; margin: 8px 0 0; font-size: 1rem; line-height: 1.55; }
.badge {
    display: inline-flex; align-items: center;
    padding: 6px 12px; margin: 6px 6px 0 0; border-radius: 999px;
    background: #eff6ff; border: 1px solid #bfdbfe;
    color: #1d4ed8; font-weight: 600; font-size: .8rem;
}
.section-title {
    font-size: .72rem; letter-spacing: .22em;
    text-transform: uppercase; color: #64748b;
    font-weight: 800; margin: 24px 0 12px;
}
.card {
    background: #fff; border: 1px solid #e5edf5;
    border-radius: 18px; padding: 20px;
    box-shadow: 0 8px 22px rgba(15,23,42,.04);
    margin-bottom: 14px;
}
.metric-card {
    background: #fff; border: 1px solid #e5edf5;
    border-radius: 16px; padding: 16px;
    box-shadow: 0 4px 14px rgba(15,23,42,.04);
}
.metric-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .12em; color: #64748b; font-weight: 700; }
.metric-value { font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-top: 4px; }
.metric-sub { font-size: .8rem; color: #64748b; margin-top: 2px; }
.info-strip { background: #dbeafe; color: #1e3a8a; border: 1px solid #bfdbfe; border-radius: 12px; padding: 12px 16px; font-weight: 600; margin: 10px 0; font-size: .9rem; }
.warn-strip { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; border-radius: 12px; padding: 12px 16px; font-weight: 600; margin: 10px 0; font-size: .9rem; }
.ok-strip { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; border-radius: 12px; padding: 12px 16px; font-weight: 600; margin: 10px 0; font-size: .9rem; }
.profile-pill {
    display: inline-block; padding: 10px 16px; border-radius: 14px;
    background: linear-gradient(135deg, #2563eb, #60a5fa); color: white;
    font-weight: 700; font-size: .9rem; margin: 6px 6px 0 0;
}
.compare-input { background: linear-gradient(135deg,#f1f5f9,#e2e8f0); border: 1px solid #cbd5e1; border-radius: 16px; padding: 18px; }
.compare-output { background: linear-gradient(135deg,#dbeafe,#bfdbfe); border: 1px solid #93c5fd; border-radius: 16px; padding: 18px; }
.compare-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(0,0,0,.06); font-size: .9rem; }
.compare-row:last-child { border-bottom: 0; }
.compare-label { color: #64748b; font-weight: 600; }
.compare-val { color: #0f172a; font-weight: 700; }
.savings-card {
    background: linear-gradient(135deg, #059669, #10b981);
    color: white; border-radius: 18px; padding: 20px; text-align: center;
    box-shadow: 0 10px 26px rgba(5,150,105,.25);
}
.savings-value { font-size: 2.4rem; font-weight: 900; line-height: 1; }
.savings-label { font-size: .8rem; opacity: .9; text-transform: uppercase; letter-spacing: .14em; margin-top: 6px; }
.stButton>button {
    border-radius: 12px !important; border: 0 !important;
    background: linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color: #fff !important; font-weight: 700 !important;
    box-shadow: 0 8px 18px rgba(37,99,235,.22);
    padding: 10px 18px !important;
}
.stDownloadButton>button { border-radius: 12px !important; font-weight: 700 !important; }
[data-testid="stMetric"] { background: #fff; border: 1px solid #e5edf5; border-radius: 14px; padding: 14px; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { background: #fff; border: 1px solid #e5edf5; border-radius: 12px; padding: 10px 16px; font-weight: 600; }
.stTabs [aria-selected="true"] { background: #eff6ff !important; color: #1d4ed8 !important; border-color: #93c5fd !important; }
video { border-radius: 14px; background: #000; }
hr { border-color: #e5edf5; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# Cached FFmpeg detection
# ============================================================
@st.cache_resource(show_spinner=False)
def ffinfo() -> Dict[str, str]:
    ff = shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    d = {"ffmpeg": ff or "", "ffprobe": fp or "", "version": "", "encoders": "", "filters": ""}
    if ff:
        try:
            d["version"] = subprocess.check_output(
                [ff, "-version"], text=True, stderr=subprocess.STDOUT, timeout=5
            ).splitlines()[0]
            d["encoders"] = subprocess.check_output(
                [ff, "-hide_banner", "-encoders"], text=True, stderr=subprocess.STDOUT, timeout=8
            )
            d["filters"] = subprocess.check_output(
                [ff, "-hide_banner", "-filters"], text=True, stderr=subprocess.STDOUT, timeout=8
            )
        except Exception as e:
            d["version"] = f"detection error: {e}"
    return d


def has_encoder(name: str) -> bool:
    return bool(name) and name in ffinfo().get("encoders", "")


def has_filter(name: str) -> bool:
    return bool(name) and name in (ffinfo().get("filters", "") or "")


# ============================================================
# File utilities
# ============================================================
def clean(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem)[:70] or "video"


def save_upload(uploaded, folder: Path) -> Optional[Path]:
    if not uploaded:
        return None
    ext = Path(uploaded.name).suffix.lower()
    p = folder / f"{int(time.time())}_{clean(uploaded.name)}{ext}"
    p.write_bytes(uploaded.getbuffer())
    return p


@st.cache_data(show_spinner=False)
def probe_cached(path_str: str, mtime: float, size: int) -> Dict:
    """Cache key includes mtime+size so re-uploads invalidate cache."""
    if not ffinfo()["ffprobe"]:
        return {}
    try:
        out = subprocess.check_output(
            [
                ffinfo()["ffprobe"], "-v", "error",
                "-show_streams", "-show_format",
                "-print_format", "json", path_str,
            ],
            text=True, stderr=subprocess.STDOUT, timeout=25,
        )
        return json.loads(out)
    except Exception:
        return {}


def probe(p: Path) -> Dict:
    try:
        st_info = p.stat()
        return probe_cached(str(p), st_info.st_mtime, st_info.st_size)
    except Exception:
        return {}


def frac(v: str) -> float:
    try:
        a, b = v.split("/")
        return round(float(a) / float(b), 3) if float(b) else 0.0
    except Exception:
        return 0.0


def media(p: Path) -> Dict:
    d = probe(p)
    fmt = d.get("format", {}) if d else {}
    v, a = {}, {}
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and not v:
            v = s
        if s.get("codec_type") == "audio" and not a:
            a = s
    size = p.stat().st_size if p.exists() else int(fmt.get("size", 0) or 0)
    return {
        "duration": float(fmt.get("duration", 0) or 0),
        "size_mb": size / 1048576,
        "size_bytes": size,
        "bitrate_kbps": int(fmt.get("bit_rate", 0) or 0) / 1000,
        "width": int(v.get("width", 0) or 0),
        "height": int(v.get("height", 0) or 0),
        "fps": frac(v.get("avg_frame_rate", "0/1")),
        "vcodec": v.get("codec_name", "unknown"),
        "pix_fmt": v.get("pix_fmt", ""),
        "color_space": v.get("color_space", "") or "",
        "color_transfer": v.get("color_transfer", "") or "",
        "color_primaries": v.get("color_primaries", "") or "",
        "bit_depth": int(v.get("bits_per_raw_sample", 0) or 0),
        "has_audio": bool(a),
        "acodec": a.get("codec_name", ""),
        "channels": int(a.get("channels", 0) or 0),
        "sample_rate": int(a.get("sample_rate", 0) or 0),
    }


# ============================================================
# Smart source analysis: HDR + FPS recommendations
# ============================================================
def detect_hdr(meta: Dict) -> bool:
    transfer = meta.get("color_transfer", "").lower()
    primaries = meta.get("color_primaries", "").lower()
    pix = meta.get("pix_fmt", "").lower()
    bit = meta.get("bit_depth", 0)
    if any(k in transfer for k in ["smpte2084", "arib-std-b67", "pq", "hlg"]):
        return True
    if "bt2020" in primaries:
        return True
    if bit >= 10 or any(k in pix for k in ["p010", "p016", "yuv420p10", "yuv422p10", "yuv444p10"]):
        return True
    return False


def recommend_interpolation(meta: Dict) -> Tuple[bool, str]:
    fps = meta.get("fps", 0)
    if fps >= 50:
        return False, f"Source is already {fps:.2f} fps. Interpolation not recommended."
    if fps < 24:
        return True, f"Source is {fps:.2f} fps. Interpolation can improve smoothness."
    return True, f"Source is {fps:.2f} fps. Interpolation is optional."


# ============================================================
# Intent-based profiles - core encoding intelligence
# ============================================================
PROFILES = {
    "📦 Smallest File": {
        "desc": "Maximum compression for storage/upload. Higher CRF, opus 64k.",
        "av1": {"crf": 38, "preset": "6", "mbr_720p": 1500, "mbr_1080p": 2500},
        "hevc": {"crf": 30, "preset": "medium"},
        "h264": {"crf": 30, "preset": "medium"},
        "audio_aac": "96k", "audio_opus": "64k",
        "default_codec": "AV1",
    },
    "⚖️ Balanced": {
        "desc": "Recommended default. Good compression, strong quality.",
        "av1": {"crf": 34, "preset": "6", "mbr_720p": 2200, "mbr_1080p": 3500},
        "hevc": {"crf": 27, "preset": "medium"},
        "h264": {"crf": 26, "preset": "medium"},
        "audio_aac": "128k", "audio_opus": "96k",
        "default_codec": "AV1",
    },
    "🎥 High Quality": {
        "desc": "Visually high-quality master. Lower CRF, larger file.",
        "av1": {"crf": 28, "preset": "5", "mbr_720p": 3500, "mbr_1080p": 6000},
        "hevc": {"crf": 22, "preset": "slow"},
        "h264": {"crf": 20, "preset": "slow"},
        "audio_aac": "192k", "audio_opus": "128k",
        "default_codec": "HEVC (H.265)",
    },
    "🏆 Archive Master": {
        "desc": "Near-lossless archive. Very large files.",
        "av1": {"crf": 22, "preset": "4", "mbr_720p": 0, "mbr_1080p": 0},
        "hevc": {"crf": 18, "preset": "slow"},
        "h264": {"crf": 16, "preset": "slow"},
        "audio_aac": "256k", "audio_opus": "160k",
        "default_codec": "HEVC (H.265)",
    },
    "⚡ Fast Encode": {
        "desc": "Speed-optimized H.264 for quick delivery.",
        "av1": {"crf": 35, "preset": "8", "mbr_720p": 2500, "mbr_1080p": 4000},
        "hevc": {"crf": 28, "preset": "veryfast"},
        "h264": {"crf": 26, "preset": "veryfast"},
        "audio_aac": "128k", "audio_opus": "96k",
        "default_codec": "AVC (H.264)",
    },
    "📱 Social Media": {
        "desc": "Optimized for Instagram/TikTok/YouTube Shorts.",
        "av1": {"crf": 32, "preset": "6", "mbr_720p": 2500, "mbr_1080p": 4500},
        "hevc": {"crf": 26, "preset": "fast"},
        "h264": {"crf": 24, "preset": "fast"},
        "audio_aac": "128k", "audio_opus": "96k",
        "default_codec": "AVC (H.264)",
    },
}


def map_slider_to_profile(goal: int) -> str:
    """0 = highest quality, 100 = smallest file."""
    if goal <= 20:
        return "🏆 Archive Master"
    if goal <= 40:
        return "🎥 High Quality"
    if goal <= 65:
        return "⚖️ Balanced"
    if goal <= 85:
        return "📱 Social Media"
    return "📦 Smallest File"


# ============================================================
# Filter chain - smart and source-aware
# ============================================================
def build_filter_chain(opts: Dict, src_meta: Dict) -> str:
    f = []
    if opts.get("denoise"):
        f.append("hqdn3d=2:2:4:4")
    if opts.get("deblock") and has_filter("deblock"):
        f.append("deblock")
    # HDR->SDR only if source is HDR
    if opts.get("hdr_sdr") and detect_hdr(src_meta):
        if has_filter("zscale") and has_filter("tonemap"):
            f.append("zscale=t=linear:npl=100,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        else:
            f.append("format=yuv420p")
    if opts.get("color"):
        f.append("eq=contrast=1.06:saturation=1.10")
    scale_to = opts.get("scale_to", "Source")
    if scale_to and scale_to != "Source":
        h = int(scale_to.replace("p", ""))
        f.append(f"scale=-2:{h}:flags=lanczos")
    if opts.get("sharpen"):
        f.append("unsharp=5:5:0.4:3:3:0.2")
    # Interpolation only when fps < 50
    if opts.get("interp") and src_meta.get("fps", 0) < 50:
        f.append("minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    return ",".join(f)


# ============================================================
# Codec args with profile-aware settings + bitrate cap
# ============================================================
def codec_args(codec: str, crf: int, preset: str, profile: Dict, src_meta: Dict) -> Tuple[List[str], str, str]:
    width = src_meta.get("width", 1280)
    mbr_key = "mbr_1080p" if width >= 1500 else "mbr_720p"

    if codec == "AVC (H.264)":
        enc = "libx264" if has_encoder("libx264") else "h264"
        args = ["-c:v", enc, "-preset", preset, "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", profile["audio_aac"],
                "-movflags", "+faststart"]
        return args, ".mp4", "video/mp4"

    if codec == "HEVC (H.265)":
        enc = "libx265" if has_encoder("libx265") else "hevc"
        args = ["-c:v", enc, "-preset", preset, "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", profile["audio_aac"],
                "-movflags", "+faststart"]
        if enc == "libx265":
            args += ["-tag:v", "hvc1", "-x265-params", "log-level=error"]
        return args, ".mp4", "video/mp4"

    # AV1
    av1_cfg = profile["av1"]
    mbr = av1_cfg.get(mbr_key, 0)
    if has_encoder("libsvtav1"):
        svt_params = f"tune=0"
        if mbr > 0:
            svt_params += f":mbr={mbr}"
        args = ["-c:v", "libsvtav1", "-crf", str(crf), "-preset", str(av1_cfg["preset"]),
                "-svtav1-params", svt_params,
                "-pix_fmt", "yuv420p",
                "-c:a", "libopus", "-b:a", profile["audio_opus"]]
        return args, ".webm", "video/webm"
    if has_encoder("libaom-av1"):
        args = ["-c:v", "libaom-av1", "-crf", str(crf), "-b:v", "0",
                "-cpu-used", "6", "-pix_fmt", "yuv420p",
                "-c:a", "libopus", "-b:a", profile["audio_opus"]]
        return args, ".webm", "video/webm"
    # fallback
    return codec_args("AVC (H.264)", crf, preset, profile, src_meta)


# ============================================================
# Preview estimator
# ============================================================
def estimate_output(src_meta: Dict, codec: str, crf: int, enhancements: Dict) -> Dict:
    """Rough estimator based on codec efficiency and content complexity."""
    duration = src_meta.get("duration", 0)
    width = src_meta.get("width", 1280)
    height = src_meta.get("height", 720)
    src_bitrate = src_meta.get("bitrate_kbps", 0) or 2000

    # Codec efficiency factor vs source H.264
    eff = {"AV1": 0.45, "HEVC (H.265)": 0.60, "AVC (H.264)": 0.85}.get(codec, 0.85)
    # CRF factor (lower crf = bigger)
    crf_factor = 2 ** ((28 - crf) / 6.0) if crf > 0 else 1.0
    # Enhancement bitrate impact
    enh_factor = 1.0
    if enhancements.get("sharpen"):
        enh_factor *= 1.10
    if enhancements.get("color"):
        enh_factor *= 1.05
    if enhancements.get("interp") and src_meta.get("fps", 0) < 50:
        enh_factor *= 1.7
    if enhancements.get("scale_to", "Source") != "Source":
        target_h = int(enhancements["scale_to"].replace("p", ""))
        enh_factor *= max(0.4, (target_h / max(height, 1)))

    est_bitrate = max(150, src_bitrate * eff * crf_factor * enh_factor)
    est_size_mb = (est_bitrate * 1000 * duration) / 8 / 1048576 if duration else 0

    # Rough encode time multiplier
    speed_mult = {"AV1": 4.5, "HEVC (H.265)": 2.2, "AVC (H.264)": 1.0}.get(codec, 1.0)
    if enhancements.get("interp") and src_meta.get("fps", 0) < 50:
        speed_mult *= 2.5
    if enhancements.get("scale_to", "Source") in ["1080p", "2160p"]:
        speed_mult *= 1.6
    est_time_sec = duration * speed_mult * 0.5

    return {
        "est_bitrate_kbps": int(est_bitrate),
        "est_size_mb": round(est_size_mb, 2),
        "est_time_sec": int(est_time_sec),
        "expected_savings_pct": round(max(0, (1 - est_size_mb / max(src_meta.get("size_mb", 0.001), 0.001)) * 100), 1),
    }


# ============================================================
# Encode with progress
# ============================================================
def encode_video(src: Path, logo: Optional[Path], opts: Dict, src_meta: Dict, sid: str, cb=None) -> Tuple[Optional[Path], Path, Dict]:
    log = LOG_DIR / f"{sid}.log"
    info = ffinfo()
    if not info["ffmpeg"]:
        return None, log, {"error": "FFmpeg missing. Ensure packages.txt contains `ffmpeg` and redeploy."}

    profile = PROFILES[opts["profile"]]
    codec = opts["codec"]
    crf = int(opts["crf"])
    preset = str(opts["preset"])
    args, ext, mime = codec_args(codec, crf, preset, profile, src_meta)

    out = OUT_DIR / f"{clean(src.name)}_{codec.split()[0].lower()}_crf{crf}_{sid[:8]}{ext}"
    vf = build_filter_chain(opts, src_meta)

    cmd = [info["ffmpeg"], "-hide_banner", "-y", "-i", str(src)]
    if logo and opts.get("image_mode") == "Watermark / logo overlay":
        cmd += ["-i", str(logo)]
        pos = {
            "Top right": "main_w-overlay_w-24:24",
            "Top left": "24:24",
            "Bottom right": "main_w-overlay_w-24:main_h-overlay_h-24",
            "Bottom left": "24:main_h-overlay_h-24",
        }[opts.get("logo_pos", "Top right")]
        base = vf + "," if vf else ""
        fc = (
            f"[1:v]scale=iw*{opts.get('logo_scale',14)}/100:-1[logo];"
            f"[0:v]{base}format=yuv420p[base];"
            f"[base][logo]overlay={pos}:format=auto[v]"
        )
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a?", "-shortest"]
    elif vf:
        cmd += ["-vf", vf]

    cmd += args + [str(out)]

    duration = max(src_meta.get("duration", 0.001), 0.001)
    lines: List[str] = []
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write("\n\n$ " + " ".join(map(str, cmd)) + "\n")

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        last = 0.0
        assert proc.stderr is not None
        for line in proc.stderr:
            lines.append(line.rstrip())
            with log.open("a", encoding="utf-8") as f:
                f.write(line)
            m = re.search(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", line)
            if m and cb:
                sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
                pct = min(max(sec / duration, last), 0.995)
                last = pct
                try:
                    cb(pct, f"Encoding… {pct*100:.0f}%")
                except Exception:
                    pass
        rc = proc.wait()
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n[exit] {rc}\n")
        if cb:
            cb(1.0, "Encoding complete")
        if rc != 0 or not out.exists():
            return None, log, {"error": "Encoding failed", "tail": "\n".join(lines[-100:])}
        return out, log, {"mime": mime}
    except Exception as e:
        return None, log, {"error": str(e), "tail": "\n".join(lines[-100:])}


# ============================================================
# Quality metrics
# ============================================================
def run_ffmpeg(cmd, log, timeout=900):
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout,
        )
        with log.open("a", encoding="utf-8") as f:
            f.write("\n$ " + " ".join(map(str, cmd)) + "\n" + (p.stdout or ""))
        return p.stdout or ""
    except Exception as e:
        return str(e)


def quality_metrics(ref: Path, dist: Path, sid: str, quick: bool = True) -> Dict:
    res: Dict = {}
    info = ffinfo()
    if not info["ffmpeg"]:
        return res
    log = LOG_DIR / f"{sid}.log"
    mm = media(ref)
    w, h = mm.get("width", 0), mm.get("height", 0)
    scale = f"scale={w}:{h}:flags=bicubic" if w and h else "null"
    limit = ["-t", "60"] if quick else []
    graph = (
        f"[0:v]setpts=PTS-STARTPTS,{scale},format=yuv420p,split=2[r1][r2];"
        f"[1:v]setpts=PTS-STARTPTS,{scale},format=yuv420p,split=2[d1][d2];"
        f"[r1][d1]psnr;[r2][d2]ssim"
    )
    out = run_ffmpeg(
        [info["ffmpeg"], "-hide_banner", "-nostats", "-i", str(ref), "-i", str(dist)]
        + limit + ["-lavfi", graph, "-f", "null", "-"],
        log, 600,
    )
    m = re.search(r"average:([0-9.]+|inf)", out)
    if m:
        res["PSNR"] = 100.0 if m.group(1) == "inf" else float(m.group(1))
    m = re.search(r"All:([0-9.]+)", out)
    if m:
        res["SSIM"] = float(m.group(1))

    if has_filter("libvmaf"):
        js = LOG_DIR / f"{sid}_vmaf.json"
        graph_v = (
            f"[0:v]setpts=PTS-STARTPTS,{scale},format=yuv420p[ref];"
            f"[1:v]setpts=PTS-STARTPTS,{scale},format=yuv420p[dst];"
            f"[dst][ref]libvmaf=log_fmt=json:log_path={js}"
        )
        run_ffmpeg(
            [info["ffmpeg"], "-hide_banner", "-nostats", "-i", str(ref), "-i", str(dist)]
            + limit + ["-lavfi", graph_v, "-f", "null", "-"],
            log, 900,
        )
        try:
            data = json.loads(js.read_text())
            res["VMAF"] = float(data.get("pooled_metrics", {}).get("vmaf", {}).get("mean"))
        except Exception:
            pass
    elif res.get("SSIM"):
        res["VMAF_proxy"] = round(max(0, min(100, 100 * (res["SSIM"] ** 0.45))), 2)
    return res


# ============================================================
# CSV session log
# ============================================================
def csvrow(row: Dict):
    p = LOG_DIR / "sessions.csv"
    new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)


# ============================================================
# Universal HTML player + side-by-side
# ============================================================
def player(path: Path, poster: Optional[Path], mime: str):
    if not path or not path.exists():
        return
    # large files -> use native st.video to avoid base64 memory blowup
    if path.stat().st_size > 80 * 1024 * 1024:
        st.video(str(path))
        return
    vb64 = base64.b64encode(path.read_bytes()).decode()
    pa = ""
    if poster and poster.exists():
        pm = "image/png" if poster.suffix.lower() == ".png" else "image/jpeg"
        pa = f"poster='data:{pm};base64,{base64.b64encode(poster.read_bytes()).decode()}'"
    components.html(
        f"""
        <div style='background:#fff;border:1px solid #e5edf5;border-radius:14px;padding:10px;'>
            <video controls preload='metadata' style='width:100%;max-height:520px;background:#000;border-radius:10px' {pa}>
                <source src='data:{mime};base64,{vb64}' type='{mime}'>
            </video>
        </div>
        """,
        height=560,
    )


# ============================================================
# HLS ABR ladder
# ============================================================
def make_hls(src: Path, sid: str) -> Tuple[Path, Path]:
    log = LOG_DIR / f"{sid}.log"
    od = OUT_DIR / f"abr_{sid[:8]}"
    od.mkdir(exist_ok=True)
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for w, h, br in [(426, 240, "400k"), (854, 480, "900k"), (1280, 720, "2200k")]:
        name = f"{h}p.m3u8"
        cmd = [
            ffinfo()["ffmpeg"], "-hide_banner", "-y", "-i", str(src),
            "-vf",
            f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264" if has_encoder("libx264") else "h264",
            "-preset", "veryfast",
            "-b:v", br, "-maxrate", br,
            "-bufsize", str(int(br[:-1]) * 2) + "k",
            "-c:a", "aac", "-b:a", "96k",
            "-f", "hls", "-hls_time", "4", "-hls_playlist_type", "vod",
            "-hls_segment_filename", str(od / f"{h}p_%03d.ts"),
            str(od / name),
        ]
        try:
            subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=1800,
            )
        except Exception:
            pass
        if (od / name).exists():
            lines += [
                f"#EXT-X-STREAM-INF:BANDWIDTH={int(br[:-1])*1000},RESOLUTION={w}x{h}",
                name,
            ]
    master = od / "master.m3u8"
    master.write_text("\n".join(lines), encoding="utf-8")
    return master, log


# ============================================================
# Render helpers
# ============================================================
def render_metric(label: str, value: str, sub: str = ""):
    sub_html = f"<div class='metric-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div>"
        f"<div class='metric-value'>{value}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )


def render_compare_row(left_html: str, right_html: str, label: str, l_val: str, r_val: str):
    return f"<div class='compare-row'><span class='compare-label'>{label}</span><span class='compare-val'>{l_val}</span></div>"


# ============================================================
# Session state init
# ============================================================
for k in ["src", "out", "img", "src_meta", "last_metrics", "last_md", "last_log"]:
    if k not in st.session_state:
        st.session_state[k] = None


# ============================================================
# Header
# ============================================================
info = ffinfo()
av1_ready = has_encoder("libsvtav1") or has_encoder("libaom-av1")

st.markdown(
    f"""
<div class='hero'>
  <h1>🎬 VideoForge Studio</h1>
  <p>Professional video optimization platform — intent-based encoding, smart enhancements, and side-by-side quality analytics.</p>
  <div style='margin-top:12px'>
    <span class='badge'>{'✅' if info['ffmpeg'] else '❌'} FFmpeg</span>
    <span class='badge'>{'✅' if has_encoder('libx264') else '⚠️'} H.264</span>
    <span class='badge'>{'✅' if has_encoder('libx265') else '⚠️'} HEVC</span>
    <span class='badge'>{'✅' if av1_ready else '⚠️'} AV1</span>
    <span class='badge'>{'✅' if has_filter('libvmaf') else '⚠️'} VMAF</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if not info["ffmpeg"]:
    st.error("FFmpeg is missing. Repo must contain `packages.txt` (exact name) with `ffmpeg` inside, then redeploy.")
    st.stop()

# ============================================================
# Tabs (workflow-based)
# ============================================================
tab_work, tab_compare, tab_player, tab_quality, tab_sweep, tab_abr, tab_logs = st.tabs(
    ["🛠️ Workflow", "🆚 Compare", "▶️ Player", "📊 Quality", "📈 CRF Sweep", "📡 ABR", "🪵 Logs"]
)

# ============================================================
# WORKFLOW TAB
# ============================================================
with tab_work:
    # Step 1: Upload
    st.markdown("<div class='section-title'>Step 1 · Upload</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    cu1, cu2 = st.columns([1.2, 0.8], gap="large")
    with cu1:
        up = st.file_uploader(
            "Source video",
            type=["mp4", "mov", "mkv", "webm", "avi", "m4v", "ts"],
            key="upload_src",
        )
        if up:
            p = save_upload(up, IN_DIR)
            st.session_state.src = str(p)
            st.session_state.src_meta = media(p)
            st.success(f"Loaded: {p.name}")
    with cu2:
        im = st.file_uploader(
            "Image / logo / poster",
            type=["png", "jpg", "jpeg", "webp"],
            key="upload_img",
        )
        if im:
            ip = save_upload(im, IN_DIR)
            st.session_state.img = str(ip)
            st.image(str(ip), caption="Attached image", use_container_width=True)

    src_meta = st.session_state.src_meta or {}
    if src_meta:
        is_hdr = detect_hdr(src_meta)
        interp_ok, interp_msg = recommend_interpolation(src_meta)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: render_metric("Resolution", f"{src_meta['width']}×{src_meta['height']}")
        with c2: render_metric("Codec", src_meta["vcodec"].upper())
        with c3: render_metric("FPS", f"{src_meta['fps']:.2f}")
        with c4: render_metric("Bitrate", f"{src_meta['bitrate_kbps']:.0f} kbps")
        with c5: render_metric("Size", f"{src_meta['size_mb']:.2f} MB")

        st.markdown(
            f"<div class='{ 'warn-strip' if is_hdr else 'ok-strip' }'>"
            f"{'⚠️ HDR source detected (' + (src_meta.get('color_transfer') or 'HDR') + ')' if is_hdr else '✅ SDR source detected — HDR conversion will be disabled.'}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='{'warn-strip' if not interp_ok else 'info-strip'}'>🎞️ {interp_msg}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Step 2: Optimization Goal
    st.markdown("<div class='section-title'>Step 2 · Optimization Goal</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    goal = st.slider("Quality ◄────────► Size", 0, 100, 55, help="0 = max quality, 100 = smallest file")
    profile_name = map_slider_to_profile(goal)
    profile_name = st.selectbox(
        "Profile (override)",
        list(PROFILES.keys()),
        index=list(PROFILES.keys()).index(profile_name),
    )
    profile = PROFILES[profile_name]
    st.markdown(f"<div class='info-strip'>{profile['desc']}</div>", unsafe_allow_html=True)

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        codec = st.selectbox(
            "Codec",
            ["AVC (H.264)", "HEVC (H.265)", "AV1"],
            index=["AVC (H.264)", "HEVC (H.265)", "AV1"].index(profile["default_codec"]),
        )
    # Profile-driven CRF + preset defaults, then allow override
    if codec == "AV1":
        default_crf = profile["av1"]["crf"]
        default_preset = profile["av1"]["preset"]
        preset_opts = ["4", "5", "6", "7", "8"]
    elif codec == "HEVC (H.265)":
        default_crf = profile["hevc"]["crf"]
        default_preset = profile["hevc"]["preset"]
        preset_opts = ["veryfast", "fast", "medium", "slow"]
    else:
        default_crf = profile["h264"]["crf"]
        default_preset = profile["h264"]["preset"]
        preset_opts = ["veryfast", "fast", "medium", "slow"]

    with pc2:
        crf = st.slider("CRF (override)", 14, 45, default_crf,
                        help="Lower = higher quality + larger file. AV1 typical 28–38.")
    with pc3:
        try:
            preset_idx = preset_opts.index(str(default_preset))
        except ValueError:
            preset_idx = 0
        preset = st.selectbox("Preset (override)", preset_opts, index=preset_idx)
    st.markdown("</div>", unsafe_allow_html=True)

    # Step 3: Enhancements
    st.markdown("<div class='section-title'>Step 3 · Enhancements</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    with st.expander("🛡️ Quality enhancement", expanded=True):
        e1, e2, e3 = st.columns(3)
        denoise = e1.checkbox("Denoise", value=False)
        deblock = e2.checkbox("Deblock", value=False)
        sharpen = e3.checkbox("Sharpen", value=False)

    with st.expander("🎨 Color processing", expanded=False):
        c1, c2 = st.columns(2)
        color = c1.checkbox("Color boost", value=False)
        # Smart HDR toggle - disabled if SDR
        is_hdr_src = detect_hdr(src_meta) if src_meta else False
        hdr_sdr = c2.checkbox(
            "HDR → SDR",
            value=is_hdr_src,
            disabled=not is_hdr_src,
            help="Only enabled when source is HDR.",
        )

    with st.expander("🎞️ Motion processing", expanded=False):
        interp_recommended, _ = recommend_interpolation(src_meta) if src_meta else (True, "")
        interp = st.checkbox(
            "Frame interpolation → 60fps",
            value=False,
            disabled=not interp_recommended,
            help="Disabled when source already ≥ 50 fps.",
        )

    with st.expander("📐 Resolution", expanded=False):
        scale_to = st.selectbox(
            "Target size",
            ["Source", "480p", "720p", "1080p", "2160p"],
            index=0,
        )

    with st.expander("🖼️ Image / logo overlay", expanded=False):
        image_mode = st.selectbox(
            "Attached image behavior",
            ["Ignore image", "Watermark / logo overlay", "Poster only in player"],
            index=1 if st.session_state.img else 0,
        )
        lc1, lc2 = st.columns(2)
        logo_pos = lc1.selectbox("Logo position", ["Top right", "Top left", "Bottom right", "Bottom left"])
        logo_scale = lc2.slider("Logo scale %", 5, 35, 14)
    st.markdown("</div>", unsafe_allow_html=True)

    # Step 4: Preview Impact
    st.markdown("<div class='section-title'>Step 4 · Preview Impact</div>", unsafe_allow_html=True)
    enhancements = dict(
        denoise=denoise, sharpen=sharpen, deblock=deblock, color=color,
        hdr_sdr=hdr_sdr, interp=interp, scale_to=scale_to,
    )
    if src_meta:
        est = estimate_output(src_meta, codec, crf, enhancements)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1: render_metric("Est. Output Size", f"{est['est_size_mb']:.2f} MB")
        with pc2: render_metric("Est. Bitrate", f"{est['est_bitrate_kbps']} kbps")
        with pc3: render_metric("Expected Savings", f"{est['expected_savings_pct']:.1f}%")
        with pc4:
            m = est["est_time_sec"]
            render_metric("Est. Encode Time", f"{m//60}m {m%60}s")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Upload a source video to see estimates.")

    # Step 5: Encode
    st.markdown("<div class='section-title'>Step 5 · Encode</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    go = st.button("✨ Encode Now", type="primary", use_container_width=True)
    if go:
        if not st.session_state.src:
            st.error("Upload a source video first.")
        else:
            sid = uuid.uuid4().hex
            src = Path(st.session_state.src)
            logo = Path(st.session_state.img) if st.session_state.img else None
            o = dict(
                codec=codec, crf=crf, preset=preset, profile=profile_name,
                denoise=denoise, sharpen=sharpen, deblock=deblock, color=color,
                hdr_sdr=hdr_sdr, interp=interp, scale_to=scale_to,
                image_mode=image_mode, logo_pos=logo_pos, logo_scale=logo_scale,
            )
            bar = st.progress(0.0, text="Starting FFmpeg encode…")
            out_path, log, md = encode_video(
                src, logo, o, src_meta, sid,
                cb=lambda p, t: bar.progress(float(p), text=t),
            )
            if not out_path:
                st.error(md.get("error", "Encoding failed"))
                if md.get("tail"):
                    st.code(md["tail"])
            else:
                st.session_state.out = str(out_path)
                st.session_state.last_md = md
                st.session_state.last_log = str(log)
                with st.spinner("Computing quality metrics…"):
                    q = quality_metrics(src, out_path, sid, quick=True)
                st.session_state.last_metrics = q
                sm = src_meta
                dm = media(out_path)
                saved = (1 - dm["size_mb"] / sm["size_mb"]) * 100 if sm["size_mb"] else 0
                row = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "source": src.name, "output": out_path.name,
                    "profile": profile_name, "codec": codec, "crf": crf, "preset": preset,
                    "source_mb": round(sm["size_mb"], 3),
                    "output_mb": round(dm["size_mb"], 3),
                    "saved_pct": round(saved, 2),
                    "PSNR": q.get("PSNR"), "SSIM": q.get("SSIM"),
                    "VMAF": q.get("VMAF"), "VMAF_proxy": q.get("VMAF_proxy"),
                    "log": str(log),
                }
                csvrow(row)
                st.success(f"Done · {dm['size_mb']:.2f} MB · saved {saved:.1f}% · See Compare tab")
                st.download_button(
                    "⬇ Download Output",
                    out_path.read_bytes(),
                    out_path.name,
                    md.get("mime", "application/octet-stream"),
                )
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# COMPARE TAB - Input vs Output dashboard + quality dashboard
# ============================================================
with tab_compare:
    if not (st.session_state.src and st.session_state.out and Path(st.session_state.out).exists()):
        st.info("Run an encode first (Workflow tab) to see the comparison dashboard.")
    else:
        src = Path(st.session_state.src)
        out = Path(st.session_state.out)
        sm = media(src)
        dm = media(out)
        q = st.session_state.last_metrics or {}
        saved_pct = (1 - dm["size_mb"] / sm["size_mb"]) * 100 if sm["size_mb"] else 0
        br_save = (1 - dm["bitrate_kbps"] / sm["bitrate_kbps"]) * 100 if sm["bitrate_kbps"] else 0

        st.markdown("<div class='section-title'>Input vs Output</div>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns([1, 1, 1])
        with cc1:
            st.markdown(
                f"""
                <div class='compare-input'>
                    <div style='font-weight:800;font-size:1rem;margin-bottom:10px;color:#475569'>📥 INPUT</div>
                    <div class='compare-row'><span class='compare-label'>Size</span><span class='compare-val'>{sm['size_mb']:.2f} MB</span></div>
                    <div class='compare-row'><span class='compare-label'>Codec</span><span class='compare-val'>{sm['vcodec'].upper()}</span></div>
                    <div class='compare-row'><span class='compare-label'>Bitrate</span><span class='compare-val'>{sm['bitrate_kbps']:.0f} kbps</span></div>
                    <div class='compare-row'><span class='compare-label'>Resolution</span><span class='compare-val'>{sm['width']}×{sm['height']}</span></div>
                    <div class='compare-row'><span class='compare-label'>FPS</span><span class='compare-val'>{sm['fps']:.2f}</span></div>
                    <div class='compare-row'><span class='compare-label'>Duration</span><span class='compare-val'>{sm['duration']:.1f}s</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cc2:
            st.markdown(
                f"""
                <div class='savings-card'>
                    <div class='savings-value'>{saved_pct:+.1f}%</div>
                    <div class='savings-label'>Size Reduction</div>
                    <div style='margin-top:12px;font-size:.85rem;opacity:.95'>Bitrate {br_save:+.1f}%</div>
                    <div style='margin-top:6px;font-size:.85rem;opacity:.95'>Saved {(sm['size_mb']-dm['size_mb']):.2f} MB</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cc3:
            st.markdown(
                f"""
                <div class='compare-output'>
                    <div style='font-weight:800;font-size:1rem;margin-bottom:10px;color:#1e3a8a'>📤 OUTPUT</div>
                    <div class='compare-row'><span class='compare-label'>Size</span><span class='compare-val'>{dm['size_mb']:.2f} MB</span></div>
                    <div class='compare-row'><span class='compare-label'>Codec</span><span class='compare-val'>{dm['vcodec'].upper()}</span></div>
                    <div class='compare-row'><span class='compare-label'>Bitrate</span><span class='compare-val'>{dm['bitrate_kbps']:.0f} kbps</span></div>
                    <div class='compare-row'><span class='compare-label'>Resolution</span><span class='compare-val'>{dm['width']}×{dm['height']}</span></div>
                    <div class='compare-row'><span class='compare-label'>FPS</span><span class='compare-val'>{dm['fps']:.2f}</span></div>
                    <div class='compare-row'><span class='compare-label'>Duration</span><span class='compare-val'>{dm['duration']:.1f}s</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div class='section-title'>Quality Dashboard</div>", unsafe_allow_html=True)
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            vmaf_val = q.get("VMAF", q.get("VMAF_proxy"))
            render_metric("VMAF", f"{vmaf_val:.2f}" if vmaf_val else "—",
                          "True VMAF" if q.get("VMAF") else "Proxy from SSIM")
        with q2:
            render_metric("SSIM", f"{q.get('SSIM', 0):.4f}" if q.get("SSIM") else "—",
                          "0.95+ Good · 0.98+ Excellent")
        with q3:
            render_metric("PSNR", f"{q.get('PSNR', 0):.2f} dB" if q.get("PSNR") else "—",
                          "40+ dB Good")
        with q4:
            ratio = sm["size_mb"] / dm["size_mb"] if dm["size_mb"] else 0
            render_metric("Compression Ratio", f"{ratio:.2f}×", "Size reduction factor")

        st.markdown("<div class='section-title'>Side-by-Side Playback</div>", unsafe_allow_html=True)
        sbs1, sbs2 = st.columns(2)
        poster = Path(st.session_state.img) if st.session_state.img and Path(st.session_state.img).exists() else None
        with sbs1:
            st.markdown("**Original**")
            player(src, poster, "video/mp4")
        with sbs2:
            st.markdown("**Encoded**")
            mime_out = "video/webm" if out.suffix.lower() == ".webm" else "video/mp4"
            player(out, poster, mime_out)

        if st.session_state.last_md:
            st.download_button(
                "⬇ Download Encoded Video",
                out.read_bytes(), out.name,
                st.session_state.last_md.get("mime", "application/octet-stream"),
            )

# ============================================================
# PLAYER TAB (Universal + WebRTC behind expander)
# ============================================================
with tab_player:
    st.markdown("<div class='section-title'>Universal Player</div>", unsafe_allow_html=True)
    p = None
    if st.session_state.out and Path(st.session_state.out).exists():
        p = Path(st.session_state.out)
        st.caption(f"Loaded latest output: {p.name}")
    else:
        up_p = st.file_uploader("Upload media", type=["mp4", "webm", "mov", "mkv"], key="play_up")
        if up_p:
            p = save_upload(up_p, IN_DIR)
    if p:
        poster = Path(st.session_state.img) if st.session_state.img and Path(st.session_state.img).exists() else None
        mime = "video/webm" if p.suffix.lower() == ".webm" else "video/mp4"
        player(p, poster, mime)

    with st.expander("🎥 Experimental: WebRTC Camera Preview", expanded=False):
        st.caption("WebRTC may fail on free cloud runtimes. Only used for live camera preview, not playback.")
        if WEBRTC_AVAILABLE:
            enable = st.checkbox("Enable camera preview", value=False)
            if enable:
                try:
                    webrtc_streamer(
                        key="webrtc-v2",
                        rtc_configuration=RTCConfiguration(
                            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
                        ),
                        media_stream_constraints={"video": True, "audio": False},
                        async_processing=True,
                    )
                except Exception as e:
                    st.warning(f"WebRTC failed: {e}")
        else:
            st.warning("streamlit-webrtc not installed.")

# ============================================================
# QUALITY TAB
# ============================================================
with tab_quality:
    st.markdown("<div class='section-title'>Quality Analytics</div>", unsafe_allow_html=True)
    qa, qb = st.columns(2)
    rf = qa.file_uploader("Reference / source", type=["mp4", "mov", "mkv", "webm"], key="ref_up")
    df_file = qb.file_uploader("Distorted / encoded", type=["mp4", "mov", "mkv", "webm"], key="dist_up")
    full = st.checkbox("Full duration (slower)", value=False)
    if st.button("Calculate PSNR / SSIM / VMAF", use_container_width=True):
        if not rf or not df_file:
            st.error("Upload both files.")
        else:
            sid = uuid.uuid4().hex
            rp = save_upload(rf, IN_DIR)
            dp = save_upload(df_file, IN_DIR)
            with st.spinner("Computing metrics…"):
                qm = quality_metrics(rp, dp, sid, quick=not full)
            q1, q2, q3 = st.columns(3)
            with q1: render_metric("PSNR", f"{qm.get('PSNR', 0):.2f} dB" if qm.get("PSNR") else "—")
            with q2: render_metric("SSIM", f"{qm.get('SSIM', 0):.4f}" if qm.get("SSIM") else "—")
            with q3:
                v = qm.get("VMAF", qm.get("VMAF_proxy"))
                render_metric("VMAF", f"{v:.2f}" if v else "—",
                              "True VMAF" if qm.get("VMAF") else "Proxy")

# ============================================================
# CRF SWEEP TAB
# ============================================================
with tab_sweep:
    st.markdown("<div class='section-title'>Rate-Distortion Sweep</div>", unsafe_allow_html=True)
    src_path = st.session_state.src
    if not src_path:
        su = st.file_uploader("Upload source for sweep", type=["mp4", "mov", "mkv", "webm"], key="sweep_up")
        if su:
            sp = save_upload(su, IN_DIR)
            st.session_state.src = str(sp)
            st.session_state.src_meta = media(sp)
            src_path = str(sp)

    sw1, sw2, sw3, sw4 = st.columns(4)
    sw_codec = sw1.selectbox("Codec", ["AVC (H.264)", "HEVC (H.265)", "AV1"], key="sweep_codec_v2")
    sw_profile = sw2.selectbox("Profile", list(PROFILES.keys()), index=1, key="sweep_profile_v2")
    sw_start = sw3.number_input("CRF start", 14, 45, 22, key="sweep_start_v2")
    sw_end = sw4.number_input("CRF end", int(sw_start) + 1, 51, 38, key="sweep_end_v2")
    sw_step = st.slider("Step", 1, 10, 4, key="sweep_step_v2")

    if st.button("🚀 Run CRF Sweep", type="primary"):
        if not src_path:
            st.error("Upload a source first.")
        else:
            src = Path(src_path)
            sm = media(src)
            crfs = list(range(int(sw_start), int(sw_end) + 1, int(sw_step)))
            rows = []
            prog = st.progress(0, text="Starting sweep…")
            for i, cval in enumerate(crfs):
                sid = uuid.uuid4().hex
                opts = dict(
                    codec=sw_codec, crf=cval, preset="fast" if sw_codec != "AV1" else "6",
                    profile=sw_profile,
                    denoise=False, sharpen=False, deblock=False, color=False,
                    hdr_sdr=False, interp=False, scale_to="Source",
                    image_mode="Ignore image", logo_pos="Top right", logo_scale=14,
                )
                out_p, log, md = encode_video(
                    src, None, opts, sm, sid,
                    cb=lambda p, t, i=i: prog.progress(min(0.99, (i + p) / len(crfs)),
                                                       text=f"CRF {cval} · {t}"),
                )
                if out_p:
                    qm = quality_metrics(src, out_p, sid, quick=True)
                    dm = media(out_p)
                    rows.append({
                        "CRF": cval,
                        "Size MB": round(dm["size_mb"], 2),
                        "Bitrate kbps": round(dm["bitrate_kbps"]),
                        "PSNR": qm.get("PSNR"),
                        "SSIM": qm.get("SSIM"),
                        "VMAF": qm.get("VMAF", qm.get("VMAF_proxy")),
                        "File": out_p.name,
                    })
            prog.progress(1.0, text="Sweep complete")
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
                chart_cols = [c for c in ["Size MB", "VMAF", "SSIM"] if c in df.columns and df[c].notna().any()]
                if chart_cols:
                    st.line_chart(df.set_index("CRF")[chart_cols])
                st.download_button(
                    "⬇ Download CSV",
                    df.to_csv(index=False).encode(),
                    "crf_sweep.csv", "text/csv",
                )

# ============================================================
# ABR TAB
# ============================================================
with tab_abr:
    st.markdown("<div class='section-title'>Adaptive Bitrate Ladder (HLS)</div>", unsafe_allow_html=True)
    src_abr = None
    if st.session_state.out and Path(st.session_state.out).exists():
        src_abr = Path(st.session_state.out)
        st.caption(f"Using latest output: {src_abr.name}")
    else:
        au = st.file_uploader("Upload for ABR", type=["mp4", "mov", "mkv", "webm"], key="abr_up")
        if au:
            src_abr = save_upload(au, IN_DIR)
    if st.button("Generate HLS ABR Ladder", type="primary"):
        if not src_abr:
            st.error("Upload or encode first.")
        else:
            sid = uuid.uuid4().hex
            with st.spinner("Building 240p / 480p / 720p ladder…"):
                master, log = make_hls(src_abr, sid)
            zp = OUT_DIR / f"abr_package_{int(time.time())}.zip"
            with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
                for pf in master.parent.glob("*"):
                    z.write(pf, pf.name)
            st.success("ABR ladder ready")
            st.code(master.read_text())
            st.download_button(
                "⬇ Download ABR Package",
                zp.read_bytes(), zp.name, "application/zip",
            )

# ============================================================
# LOGS TAB
# ============================================================
with tab_logs:
    st.markdown("<div class='section-title'>Session Logs</div>", unsafe_allow_html=True)
    csv_p = LOG_DIR / "sessions.csv"
    if csv_p.exists():
        df = pd.read_csv(csv_p)
        st.dataframe(df.tail(200), use_container_width=True)
        st.download_button(
            "⬇ Download sessions CSV",
            csv_p.read_bytes(), "sessions.csv", "text/csv",
        )
    else:
        st.info("No sessions yet.")
    logs = sorted(LOG_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    if logs:
        sel = st.selectbox("Log file", logs, format_func=lambda x: x.name)
        st.text_area("Preview", sel.read_text(errors="ignore")[-10000:], height=320)
        st.download_button(
            "⬇ Download selected log",
            sel.read_bytes(), sel.name, "text/plain",
        )

    with st.expander("🔧 Diagnostics"):
        st.write("FFmpeg:", "✅ Ready" if info["ffmpeg"] else "❌ Missing")
        st.caption(info.get("version", ""))
        st.write("FFprobe:", "✅ Ready" if info["ffprobe"] else "❌ Missing")
        st.write(
            f"x264 {'✅' if has_encoder('libx264') else '⚠️'} · "
            f"x265 {'✅' if has_encoder('libx265') else '⚠️'} · "
            f"AV1 {'✅' if av1_ready else '⚠️'} · "
            f"libvmaf {'✅' if has_filter('libvmaf') else '⚠️'}"
        )
        st.info("If FFmpeg is missing, ensure `packages.txt` exists in repo root with `ffmpeg` inside.")
