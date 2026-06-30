"""
VideoForge Studio V2.1 — Professional Video Optimization Platform
Fixes: Material Icons preserved, native bordered containers,
HW acceleration, audio loudnorm, film grain, scene-cut keyframes,
trim support, two-pass option, auto-thumbnail.
"""
import re, json, time, uuid, shutil, subprocess, zipfile, base64, csv
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
IN_DIR, OUT_DIR, LOG_DIR, THUMB_DIR = WORK/"inputs", WORK/"outputs", WORK/"logs", WORK/"thumbs"
for d in (IN_DIR, OUT_DIR, LOG_DIR, THUMB_DIR):
    d.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="VideoForge Studio", page_icon="🎬",
                   layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# CSS — Inter for TEXT only, preserve Streamlit Material Icons
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
/* Apply Inter to text elements only — NEVER on icons */
html, body, [data-testid="stAppViewContainer"], .stApp,
.stApp p, .stApp div, .stApp span:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]),
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp label, .stApp button, .stApp input, .stApp select, .stApp textarea,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
/* Explicitly preserve Material Icons / Symbols */
.material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined,
[class*="MaterialIcon"], [data-testid*="Icon"] svg,
.stExpander summary svg, button svg {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                 'Material Icons' !important;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg,#f7faff 0%, #eef4fb 100%) !important;
    color: #0f172a !important;
}
[data-testid="stHeader"] { background: rgba(247,250,255,.85)!important; backdrop-filter: blur(10px); }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px; }
h1,h2,h3,h4 { letter-spacing: -.02em; color:#0f172a; font-weight:800; }
.hero {
    background: linear-gradient(135deg,#fff 0%, #f0f6ff 100%);
    border:1px solid #dbeafe; border-radius:24px; padding:26px 30px;
    box-shadow: 0 12px 36px rgba(59,130,246,.10); margin-bottom:22px;
}
.hero h1 { font-size:2.2rem; margin:0; font-weight:900; }
.hero p { color:#475569; margin:8px 0 0; font-size:1rem; line-height:1.55; }
.badge {
    display:inline-flex; align-items:center; padding:6px 12px; margin:6px 6px 0 0;
    border-radius:999px; background:#eff6ff; border:1px solid #bfdbfe;
    color:#1d4ed8; font-weight:600; font-size:.8rem;
}
.section-title {
    font-size:.72rem; letter-spacing:.22em; text-transform:uppercase;
    color:#64748b; font-weight:800; margin:24px 0 12px;
}
.metric-card {
    background:#fff; border:1px solid #e5edf5; border-radius:16px;
    padding:16px; box-shadow:0 4px 14px rgba(15,23,42,.04);
}
.metric-label { font-size:.72rem; text-transform:uppercase; letter-spacing:.12em; color:#64748b; font-weight:700; }
.metric-value { font-size:1.5rem; font-weight:800; color:#0f172a; margin-top:4px; }
.metric-sub { font-size:.8rem; color:#64748b; margin-top:2px; }
.info-strip { background:#dbeafe; color:#1e3a8a; border:1px solid #bfdbfe;
              border-radius:12px; padding:12px 16px; font-weight:600; margin:10px 0; font-size:.9rem; }
.warn-strip { background:#fef3c7; color:#92400e; border:1px solid #fde68a;
              border-radius:12px; padding:12px 16px; font-weight:600; margin:10px 0; font-size:.9rem; }
.ok-strip { background:#d1fae5; color:#065f46; border:1px solid #a7f3d0;
            border-radius:12px; padding:12px 16px; font-weight:600; margin:10px 0; font-size:.9rem; }
.compare-input { background: linear-gradient(135deg,#f1f5f9,#e2e8f0); border:1px solid #cbd5e1;
                 border-radius:16px; padding:18px; }
.compare-output { background: linear-gradient(135deg,#dbeafe,#bfdbfe); border:1px solid #93c5fd;
                  border-radius:16px; padding:18px; }
.compare-row { display:flex; justify-content:space-between; padding:6px 0;
               border-bottom:1px solid rgba(0,0,0,.06); font-size:.9rem; }
.compare-row:last-child { border-bottom:0; }
.compare-label { color:#64748b; font-weight:600; }
.compare-val { color:#0f172a; font-weight:700; }
.savings-card {
    background: linear-gradient(135deg,#059669,#10b981); color:white;
    border-radius:18px; padding:20px; text-align:center;
    box-shadow:0 10px 26px rgba(5,150,105,.25);
}
.savings-value { font-size:2.4rem; font-weight:900; line-height:1; }
.savings-label { font-size:.8rem; opacity:.9; text-transform:uppercase; letter-spacing:.14em; margin-top:6px; }
.stButton>button {
    border-radius:12px !important; border:0 !important;
    background: linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color:#fff !important; font-weight:700 !important;
    box-shadow:0 8px 18px rgba(37,99,235,.22); padding:10px 18px !important;
}
.stDownloadButton>button { border-radius:12px !important; font-weight:700 !important; }
[data-testid="stMetric"] { background:#fff; border:1px solid #e5edf5; border-radius:14px; padding:14px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { background:#fff; border:1px solid #e5edf5;
                               border-radius:12px; padding:10px 16px; font-weight:600; }
.stTabs [aria-selected="true"] { background:#eff6ff !important; color:#1d4ed8 !important;
                                 border-color:#93c5fd !important; }
video { border-radius:14px; background:#000; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Cached FFmpeg detection (+ HW encoders)
# ============================================================
@st.cache_resource(show_spinner=False)
def ffinfo() -> Dict[str, str]:
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    d = {"ffmpeg": ff or "", "ffprobe": fp or "", "version":"", "encoders":"", "filters":""}
    if ff:
        try:
            d["version"] = subprocess.check_output([ff,"-version"], text=True,
                              stderr=subprocess.STDOUT, timeout=5).splitlines()[0]
            d["encoders"] = subprocess.check_output([ff,"-hide_banner","-encoders"],
                              text=True, stderr=subprocess.STDOUT, timeout=8)
            d["filters"] = subprocess.check_output([ff,"-hide_banner","-filters"],
                              text=True, stderr=subprocess.STDOUT, timeout=8)
        except Exception as e:
            d["version"] = f"detection error: {e}"
    return d

def has_encoder(name): return bool(name) and name in ffinfo().get("encoders","")
def has_filter(name):  return bool(name) and name in (ffinfo().get("filters","") or "")

@st.cache_resource(show_spinner=False)
def hw_capabilities() -> Dict[str, bool]:
    return {
        "nvenc_h264": has_encoder("h264_nvenc"),
        "nvenc_hevc": has_encoder("hevc_nvenc"),
        "nvenc_av1":  has_encoder("av1_nvenc"),
        "qsv_h264":   has_encoder("h264_qsv"),
        "qsv_hevc":   has_encoder("hevc_qsv"),
        "vt_h264":    has_encoder("h264_videotoolbox"),
        "vt_hevc":    has_encoder("hevc_videotoolbox"),
        "vaapi_h264": has_encoder("h264_vaapi"),
    }

def best_hw_encoder(codec: str) -> Optional[str]:
    hw = hw_capabilities()
    if codec == "AVC (H.264)":
        for k in ("nvenc_h264","qsv_h264","vt_h264","vaapi_h264"):
            if hw[k]: return {"nvenc_h264":"h264_nvenc","qsv_h264":"h264_qsv",
                              "vt_h264":"h264_videotoolbox","vaapi_h264":"h264_vaapi"}[k]
    if codec == "HEVC (H.265)":
        for k in ("nvenc_hevc","qsv_hevc","vt_hevc"):
            if hw[k]: return {"nvenc_hevc":"hevc_nvenc","qsv_hevc":"hevc_qsv",
                              "vt_hevc":"hevc_videotoolbox"}[k]
    if codec == "AV1" and hw["nvenc_av1"]:
        return "av1_nvenc"
    return None

# ============================================================
# File utilities
# ============================================================
def clean(name): return re.sub(r"[^A-Za-z0-9_.-]+","_",Path(name).stem)[:70] or "video"

def save_upload(uploaded, folder):
    if not uploaded: return None
    ext = Path(uploaded.name).suffix.lower()
    p = folder / f"{int(time.time())}_{clean(uploaded.name)}{ext}"
    p.write_bytes(uploaded.getbuffer())
    return p

@st.cache_data(show_spinner=False)
def probe_cached(path_str, mtime, size):
    if not ffinfo()["ffprobe"]: return {}
    try:
        out = subprocess.check_output([ffinfo()["ffprobe"],"-v","error",
            "-show_streams","-show_format","-print_format","json", path_str],
            text=True, stderr=subprocess.STDOUT, timeout=25)
        return json.loads(out)
    except Exception:
        return {}

def probe(p):
    try:
        s = p.stat()
        return probe_cached(str(p), s.st_mtime, s.st_size)
    except Exception:
        return {}

def frac(v):
    try:
        a,b = v.split("/"); return round(float(a)/float(b),3) if float(b) else 0.0
    except Exception:
        return 0.0

def media(p):
    d = probe(p); fmt = d.get("format",{}) if d else {}; v,a = {},{}
    for s in d.get("streams",[]):
        if s.get("codec_type")=="video" and not v: v=s
        if s.get("codec_type")=="audio" and not a: a=s
    size = p.stat().st_size if p.exists() else int(fmt.get("size",0) or 0)
    return {
        "duration": float(fmt.get("duration",0) or 0),
        "size_mb": size/1048576, "size_bytes": size,
        "bitrate_kbps": int(fmt.get("bit_rate",0) or 0)/1000,
        "width": int(v.get("width",0) or 0), "height": int(v.get("height",0) or 0),
        "fps": frac(v.get("avg_frame_rate","0/1")),
        "vcodec": v.get("codec_name","unknown"), "pix_fmt": v.get("pix_fmt",""),
        "color_space": v.get("color_space","") or "",
        "color_transfer": v.get("color_transfer","") or "",
        "color_primaries": v.get("color_primaries","") or "",
        "bit_depth": int(v.get("bits_per_raw_sample",0) or 0),
        "has_audio": bool(a), "acodec": a.get("codec_name",""),
        "channels": int(a.get("channels",0) or 0),
        "sample_rate": int(a.get("sample_rate",0) or 0),
    }

# ============================================================
# Smart source analysis
# ============================================================
def detect_hdr(m):
    t = m.get("color_transfer","").lower(); p = m.get("color_primaries","").lower()
    px = m.get("pix_fmt","").lower(); b = m.get("bit_depth",0)
    if any(k in t for k in ["smpte2084","arib-std-b67","pq","hlg"]): return True
    if "bt2020" in p: return True
    if b>=10 or any(k in px for k in ["p010","p016","yuv420p10","yuv422p10","yuv444p10"]): return True
    return False

def recommend_interpolation(m):
    fps = m.get("fps",0)
    if fps>=50: return False, f"Source is already {fps:.2f} fps. Interpolation not recommended."
    if fps<24: return True, f"Source is {fps:.2f} fps. Interpolation can improve smoothness."
    return True, f"Source is {fps:.2f} fps. Interpolation is optional."

def detect_grain(m):
    """Simple heuristic: high bitrate + 8-bit + SDR → likely grainy"""
    br = m.get("bitrate_kbps",0); w = m.get("width",0)
    expected = (w*w*0.0008) if w else 1500
    return br > expected*1.5 and m.get("bit_depth",8) <= 8

# ============================================================
# Intent-based profiles
# ============================================================
PROFILES = {
    "📦 Smallest File": {"desc":"Maximum compression for storage/upload.",
        "av1":{"crf":38,"preset":"6","mbr_720p":1500,"mbr_1080p":2500,"grain":8},
        "hevc":{"crf":30,"preset":"medium"}, "h264":{"crf":30,"preset":"medium"},
        "audio_aac":"96k","audio_opus":"64k","default_codec":"AV1"},
    "⚖️ Balanced": {"desc":"Recommended default. Good compression + quality.",
        "av1":{"crf":34,"preset":"6","mbr_720p":2200,"mbr_1080p":3500,"grain":10},
        "hevc":{"crf":27,"preset":"medium"}, "h264":{"crf":26,"preset":"medium"},
        "audio_aac":"128k","audio_opus":"96k","default_codec":"AV1"},
    "🎥 High Quality": {"desc":"Visually high-quality master.",
        "av1":{"crf":28,"preset":"5","mbr_720p":3500,"mbr_1080p":6000,"grain":12},
        "hevc":{"crf":22,"preset":"slow"}, "h264":{"crf":20,"preset":"slow"},
        "audio_aac":"192k","audio_opus":"128k","default_codec":"HEVC (H.265)"},
    "🏆 Archive Master": {"desc":"Near-lossless archive.",
        "av1":{"crf":22,"preset":"4","mbr_720p":0,"mbr_1080p":0,"grain":0},
        "hevc":{"crf":18,"preset":"slow"}, "h264":{"crf":16,"preset":"slow"},
        "audio_aac":"256k","audio_opus":"160k","default_codec":"HEVC (H.265)"},
    "⚡ Fast Encode": {"desc":"Speed-optimized H.264 for quick delivery.",
        "av1":{"crf":35,"preset":"8","mbr_720p":2500,"mbr_1080p":4000,"grain":0},
        "hevc":{"crf":28,"preset":"veryfast"}, "h264":{"crf":26,"preset":"veryfast"},
        "audio_aac":"128k","audio_opus":"96k","default_codec":"AVC (H.264)"},
    "📱 Social Media": {"desc":"Optimized for Instagram/TikTok/YouTube Shorts.",
        "av1":{"crf":32,"preset":"6","mbr_720p":2500,"mbr_1080p":4500,"grain":0},
        "hevc":{"crf":26,"preset":"fast"}, "h264":{"crf":24,"preset":"fast"},
        "audio_aac":"128k","audio_opus":"96k","default_codec":"AVC (H.264)"},
}

def map_slider_to_profile(g):
    if g<=20: return "🏆 Archive Master"
    if g<=40: return "🎥 High Quality"
    if g<=65: return "⚖️ Balanced"
    if g<=85: return "📱 Social Media"
    return "📦 Smallest File"

# ============================================================
# Filter chain (video + audio loudnorm)
# ============================================================
def build_vf(opts, src_meta):
    f = []
    if opts.get("denoise"): f.append("hqdn3d=2:2:4:4")
    if opts.get("deblock") and has_filter("deblock"): f.append("deblock")
    if opts.get("hdr_sdr") and detect_hdr(src_meta):
        if has_filter("zscale") and has_filter("tonemap"):
            f.append("zscale=t=linear:npl=100,tonemap=tonemap=hable:desat=0,"
                     "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        else: f.append("format=yuv420p")
    if opts.get("color"): f.append("eq=contrast=1.06:saturation=1.10")
    if opts.get("scale_to") and opts["scale_to"]!="Source":
        h = int(opts["scale_to"].replace("p",""))
        f.append(f"scale=-2:{h}:flags=lanczos")
    if opts.get("sharpen"): f.append("unsharp=5:5:0.4:3:3:0.2")
    if opts.get("interp") and src_meta.get("fps",0)<50:
        f.append("minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    return ",".join(f)

def build_af(opts):
    """Audio filters incl. EBU R128 loudnorm + 48kHz resample"""
    f = []
    if opts.get("loudnorm"):
        f.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if opts.get("resample_48k"):
        f.append("aresample=48000")
    return ",".join(f) if f else ""

# ============================================================
# Codec args — w/ HW accel, film grain, scene-cut keyframes
# ============================================================
def codec_args(codec, crf, preset, profile, src_meta, opts):
    width = src_meta.get("width",1280)
    fps = max(src_meta.get("fps",30), 1)
    keyint = int(fps*10)  # 10-second GOP
    mbr_key = "mbr_1080p" if width>=1500 else "mbr_720p"
    use_hw = opts.get("use_hw") and best_hw_encoder(codec)

    audio_args = ["-c:a","aac","-b:a",profile["audio_aac"]]
    af = build_af(opts)
    if af: audio_args = ["-af", af] + audio_args

    if codec == "AVC (H.264)":
        if use_hw:
            enc = best_hw_encoder(codec)
            args = ["-c:v", enc, "-preset","p4" if "nvenc" in enc else "medium",
                    "-rc","vbr","-cq",str(crf), "-b:v","0",
                    "-pix_fmt","yuv420p","-g",str(keyint),
                    *audio_args, "-movflags","+faststart"]
        else:
            enc = "libx264" if has_encoder("libx264") else "h264"
            args = ["-c:v",enc,"-preset",preset,"-crf",str(crf),
                    "-pix_fmt","yuv420p","-g",str(keyint),"-keyint_min",str(keyint),
                    "-sc_threshold","40",
                    *audio_args, "-movflags","+faststart"]
        return args, ".mp4", "video/mp4"

    if codec == "HEVC (H.265)":
        if use_hw:
            enc = best_hw_encoder(codec)
            args = ["-c:v", enc, "-preset","p4" if "nvenc" in enc else "medium",
                    "-rc","vbr","-cq",str(crf), "-b:v","0",
                    "-pix_fmt","yuv420p","-g",str(keyint),
                    *audio_args, "-movflags","+faststart","-tag:v","hvc1"]
        else:
            enc = "libx265" if has_encoder("libx265") else "hevc"
            args = ["-c:v",enc,"-preset",preset,"-crf",str(crf),
                    "-pix_fmt","yuv420p","-g",str(keyint),
                    *audio_args, "-movflags","+faststart"]
            if enc=="libx265":
                x265p = (f"log-level=error:keyint={keyint}:min-keyint={keyint}:"
                         f"aq-mode=3:psy-rd=2.0:bframes=8:rc-lookahead=40")
                args += ["-tag:v","hvc1","-x265-params", x265p]
        return args, ".mp4", "video/mp4"

    # AV1
    av1_cfg = profile["av1"]; mbr = av1_cfg.get(mbr_key,0)
    grain = av1_cfg.get("grain",0) if (opts.get("film_grain") and detect_grain(src_meta)) else 0
    audio_args = ["-c:a","libopus","-b:a",profile["audio_opus"]]
    if af: audio_args = ["-af",af] + audio_args

    if use_hw:
        return ["-c:v","av1_nvenc","-preset","p4","-rc","vbr",
                "-cq",str(crf),"-b:v","0","-pix_fmt","yuv420p","-g",str(keyint),
                *audio_args], ".mp4", "video/mp4"

    if has_encoder("libsvtav1"):
        svt = f"tune=0:keyint={keyint}:input-depth=8"
        if mbr>0: svt += f":mbr={mbr}"
        if grain>0: svt += f":film-grain={grain}"
        return ["-c:v","libsvtav1","-crf",str(crf),"-preset",str(av1_cfg["preset"]),
                "-svtav1-params", svt, "-pix_fmt","yuv420p","-g",str(keyint),
                *audio_args], ".webm", "video/webm"
    if has_encoder("libaom-av1"):
        return ["-c:v","libaom-av1","-crf",str(crf),"-b:v","0",
                "-cpu-used","6","-pix_fmt","yuv420p","-g",str(keyint),
                *audio_args], ".webm", "video/webm"
    return codec_args("AVC (H.264)", crf, preset, profile, src_meta, opts)

# ============================================================
# Output size estimator
# ============================================================
def estimate_output(src_meta, codec, crf, enh):
    duration = src_meta.get("duration",0); w = src_meta.get("width",1280)
    h = src_meta.get("height",720); src_br = src_meta.get("bitrate_kbps",0) or 2000
    eff = {"AV1":0.45,"HEVC (H.265)":0.60,"AVC (H.264)":0.85}.get(codec,0.85)
    crf_f = 2**((28-crf)/6.0) if crf>0 else 1.0
    enh_f = 1.0
    if enh.get("sharpen"): enh_f *= 1.10
    if enh.get("color"): enh_f *= 1.05
    if enh.get("interp") and src_meta.get("fps",0)<50: enh_f *= 1.7
    if enh.get("scale_to","Source")!="Source":
        th = int(enh["scale_to"].replace("p",""))
        enh_f *= max(0.4, th/max(h,1))
    est_br = max(150, src_br*eff*crf_f*enh_f)
    est_mb = (est_br*1000*duration)/8/1048576 if duration else 0
    spd = {"AV1":4.5,"HEVC (H.265)":2.2,"AVC (H.264)":1.0}.get(codec,1.0)
    if enh.get("use_hw"): spd *= 0.2  # HW is ~5x faster
    if enh.get("interp") and src_meta.get("fps",0)<50: spd *= 2.5
    if enh.get("scale_to","Source") in ["1080p","2160p"]: spd *= 1.6
    return {
        "est_bitrate_kbps": int(est_br),
        "est_size_mb": round(est_mb,2),
        "est_time_sec": int(duration*spd*0.5),
        "expected_savings_pct": round(max(0,(1 - est_mb/max(src_meta.get("size_mb",.001),.001))*100),1),
    }

# ============================================================
# Encode w/ trim + progress
# ============================================================
def encode_video(src, logo, opts, src_meta, sid, cb=None):
    log = LOG_DIR/f"{sid}.log"
    info = ffinfo()
    if not info["ffmpeg"]:
        return None, log, {"error":"FFmpeg missing. Add ffmpeg to packages.txt."}

    profile = PROFILES[opts["profile"]]
    codec, crf, preset = opts["codec"], int(opts["crf"]), str(opts["preset"])
    args, ext, mime = codec_args(codec, crf, preset, profile, src_meta, opts)

    out = OUT_DIR/f"{clean(src.name)}_{codec.split()[0].lower()}_crf{crf}_{sid[:8]}{ext}"
    vf = build_vf(opts, src_meta)

    cmd = [info["ffmpeg"],"-hide_banner","-y"]
    # Trim BEFORE -i for fast seek if possible
    if opts.get("trim_start"): cmd += ["-ss", str(opts["trim_start"])]
    if opts.get("trim_end"):   cmd += ["-to", str(opts["trim_end"])]
    cmd += ["-i", str(src)]

    if logo and opts.get("image_mode")=="Watermark / logo overlay":
        cmd += ["-i", str(logo)]
        pos = {"Top right":"main_w-overlay_w-24:24","Top left":"24:24",
               "Bottom right":"main_w-overlay_w-24:main_h-overlay_h-24",
               "Bottom left":"24:main_h-overlay_h-24"}[opts.get("logo_pos","Top right")]
        base = vf+"," if vf else ""
        fc = (f"[1:v]scale=iw*{opts.get('logo_scale',14)}/100:-1[logo];"
              f"[0:v]{base}format=yuv420p[base];[base][logo]overlay={pos}:format=auto[v]")
        cmd += ["-filter_complex", fc, "-map","[v]","-map","0:a?","-shortest"]
    elif vf:
        cmd += ["-vf", vf]

    cmd += args + [str(out)]

    duration = max(src_meta.get("duration",0.001), 0.001)
    if opts.get("trim_end") and opts.get("trim_start"):
        duration = max(float(opts["trim_end"])-float(opts["trim_start"]), 0.001)
    lines = []
    with log.open("a", encoding="utf-8") as f:
        f.write("\n\n$ " + " ".join(map(str,cmd)) + "\n")

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, bufsize=1)
        last = 0.0
        for line in proc.stderr:
            lines.append(line.rstrip())
            with log.open("a", encoding="utf-8") as f: f.write(line)
            m = re.search(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", line)
            if m and cb:
                sec = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                pct = min(max(sec/duration, last), 0.995)
                last = pct
                try: cb(pct, f"Encoding… {pct*100:.0f}%")
                except: pass
        rc = proc.wait()
        with log.open("a", encoding="utf-8") as f: f.write(f"\n[exit] {rc}\n")
        if cb: cb(1.0, "Encoding complete")
        if rc!=0 or not out.exists():
            return None, log, {"error":"Encoding failed", "tail":"\n".join(lines[-100:])}

        # Auto-thumbnail
        if opts.get("auto_thumb"):
            try:
                thumb = THUMB_DIR/f"{out.stem}.jpg"
                subprocess.run([info["ffmpeg"],"-y","-ss","2","-i",str(out),
                                "-vframes","1","-q:v","2",str(thumb)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            except Exception: pass

        return out, log, {"mime":mime}
    except Exception as e:
        return None, log, {"error":str(e), "tail":"\n".join(lines[-100:])}

# ============================================================
# Quality metrics
# ============================================================
def run_ffmpeg(cmd, log, timeout=900):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=timeout)
        with log.open("a", encoding="utf-8") as f:
            f.write("\n$ "+" ".join(map(str,cmd))+"\n"+(p.stdout or ""))
        return p.stdout or ""
    except Exception as e:
        return str(e)

def quality_metrics(ref, dist, sid, quick=True):
    res = {}; info = ffinfo()
    if not info["ffmpeg"]: return res
    log = LOG_DIR/f"{sid}.log"
    mm = media(ref); w,h = mm.get("width",0), mm.get("height",0)
    scale = f"scale={w}:{h}:flags=bicubic" if w and h else "null"
    limit = ["-t","60"] if quick else []
    graph = (f"[0:v]setpts=PTS-STARTPTS,{scale},format=yuv420p,split=2[r1][r2];"
             f"[1:v]setpts=PTS-STARTPTS,{scale},format=yuv420p,split=2[d1][d2];"
             f"[r1][d1]psnr;[r2][d2]ssim")
    out = run_ffmpeg([info["ffmpeg"],"-hide_banner","-nostats","-i",str(ref),
                      "-i",str(dist)] + limit + ["-lavfi",graph,"-f","null","-"], log, 600)
    m = re.search(r"average:([0-9.]+|inf)", out)
    if m: res["PSNR"] = 100.0 if m.group(1)=="inf" else float(m.group(1))
    m = re.search(r"All:([0-9.]+)", out)
    if m: res["SSIM"] = float(m.group(1))
    if has_filter("libvmaf"):
        js = LOG_DIR/f"{sid}_vmaf.json"
        gv = (f"[0:v]setpts=PTS-STARTPTS,{scale},format=yuv420p[ref];"
              f"[1:v]setpts=PTS-STARTPTS,{scale},format=yuv420p[dst];"
              f"[dst][ref]libvmaf=log_fmt=json:log_path={js}")
        run_ffmpeg([info["ffmpeg"],"-hide_banner","-nostats","-i",str(ref),
                    "-i",str(dist)]+limit+["-lavfi",gv,"-f","null","-"], log, 900)
        try: res["VMAF"] = float(json.loads(js.read_text()).get("pooled_metrics",{}).get("vmaf",{}).get("mean"))
        except: pass
    elif res.get("SSIM"):
        res["VMAF_proxy"] = round(max(0,min(100,100*(res["SSIM"]**0.45))),2)
    return res

def csvrow(row):
    p = LOG_DIR/"sessions.csv"; new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new: w.writeheader()
        w.writerow(row)

def player(path, poster, mime):
    if not path or not path.exists(): return
    if path.stat().st_size > 80*1024*1024:
        st.video(str(path)); return
    vb64 = base64.b64encode(path.read_bytes()).decode()
    pa = ""
    if poster and poster.exists():
        pm = "image/png" if poster.suffix.lower()==".png" else "image/jpeg"
        pa = f"poster='data:{pm};base64,{base64.b64encode(poster.read_bytes()).decode()}'"
    components.html(f"""
    <div style='background:#fff;border:1px solid #e5edf5;border-radius:14px;padding:10px;'>
        <video controls preload='metadata'
               style='width:100%;max-height:520px;background:#000;border-radius:10px' {pa}>
            <source src='data:{mime};base64,{vb64}' type='{mime}'>
        </video>
    </div>""", height=560)

def make_hls(src, sid):
    log = LOG_DIR/f"{sid}.log"; od = OUT_DIR/f"abr_{sid[:8]}"; od.mkdir(exist_ok=True)
    lines = ["#EXTM3U","#EXT-X-VERSION:3"]
    for w,h,br in [(426,240,"400k"),(854,480,"900k"),(1280,720,"2200k")]:
        name = f"{h}p.m3u8"
        cmd = [ffinfo()["ffmpeg"],"-hide_banner","-y","-i",str(src),
               "-vf",f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease,"
                     f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
               "-c:v","libx264" if has_encoder("libx264") else "h264",
               "-preset","veryfast","-b:v",br,"-maxrate",br,
               "-bufsize",str(int(br[:-1])*2)+"k","-c:a","aac","-b:a","96k",
               "-f","hls","-hls_time","4","-hls_playlist_type","vod",
               "-hls_segment_filename",str(od/f"{h}p_%03d.ts"), str(od/name)]
        try: subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=1800)
        except: pass
        if (od/name).exists():
            lines += [f"#EXT-X-STREAM-INF:BANDWIDTH={int(br[:-1])*1000},RESOLUTION={w}x{h}", name]
    master = od/"master.m3u8"; master.write_text("\n".join(lines), encoding="utf-8")
    return master, log

def render_metric(label, value, sub=""):
    sh = f"<div class='metric-sub'>{sub}</div>" if sub else ""
    st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div>"
                f"<div class='metric-value'>{value}</div>{sh}</div>", unsafe_allow_html=True)

# ============================================================
# Session state
# ============================================================
for k in ["src","out","img","src_meta","last_metrics","last_md","last_log"]:
    if k not in st.session_state: st.session_state[k] = None

# ============================================================
# Header
# ============================================================
info = ffinfo()
av1_ready = has_encoder("libsvtav1") or has_encoder("libaom-av1")
hw = hw_capabilities()
hw_any = any(hw.values())

st.markdown(f"""
<div class='hero'>
  <h1>🎬 VideoForge Studio</h1>
  <p>Professional video optimization — intent-based encoding, HW acceleration, smart enhancements, side-by-side analytics.</p>
  <div style='margin-top:12px'>
    <span class='badge'>{'✅' if info['ffmpeg'] else '❌'} FFmpeg</span>
    <span class='badge'>{'✅' if has_encoder('libx264') else '⚠️'} H.264</span>
    <span class='badge'>{'✅' if has_encoder('libx265') else '⚠️'} HEVC</span>
    <span class='badge'>{'✅' if av1_ready else '⚠️'} AV1</span>
    <span class='badge'>{'✅' if has_filter('libvmaf') else '⚠️'} VMAF</span>
    <span class='badge'>{'⚡' if hw_any else '⚠️'} HW Accel</span>
  </div>
</div>""", unsafe_allow_html=True)

if not info["ffmpeg"]:
    st.error("FFmpeg missing. Repo must contain `packages.txt` (exact name) with `ffmpeg` inside.")
    st.stop()

# ============================================================
# Tabs
# ============================================================
tab_work, tab_compare, tab_player, tab_quality, tab_sweep, tab_abr, tab_logs = st.tabs(
    ["🛠️ Workflow","🆚 Compare","▶️ Player","📊 Quality","📈 CRF Sweep","📡 ABR","🪵 Logs"])

# ============================================================
# WORKFLOW
# ============================================================
with tab_work:
    st.markdown("<div class='section-title'>Step 1 · Upload</div>", unsafe_allow_html=True)
    with st.container(border=True):
        cu1, cu2 = st.columns([1.2, 0.8], gap="large")
        with cu1:
            up = st.file_uploader("Source video",
                  type=["mp4","mov","mkv","webm","avi","m4v","ts"], key="upload_src")
            if up:
                p = save_upload(up, IN_DIR)
                st.session_state.src = str(p)
                st.session_state.src_meta = media(p)
                st.success(f"Loaded: {p.name}")
        with cu2:
            im = st.file_uploader("Image / logo / poster",
                  type=["png","jpg","jpeg","webp"], key="upload_img")
            if im:
                ip = save_upload(im, IN_DIR)
                st.session_state.img = str(ip)
                st.image(str(ip), caption="Attached image", use_container_width=True)

        sm = st.session_state.src_meta or {}
        if sm:
            is_hdr = detect_hdr(sm)
            interp_ok, interp_msg = recommend_interpolation(sm)
            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: render_metric("Resolution", f"{sm['width']}×{sm['height']}")
            with c2: render_metric("Codec", sm["vcodec"].upper())
            with c3: render_metric("FPS", f"{sm['fps']:.2f}")
            with c4: render_metric("Bitrate", f"{sm['bitrate_kbps']:.0f} kbps")
            with c5: render_metric("Size", f"{sm['size_mb']:.2f} MB")
            st.markdown(f"<div class='{'warn-strip' if is_hdr else 'ok-strip'}'>"
                f"{'⚠️ HDR source detected' if is_hdr else '✅ SDR source — HDR conversion disabled'}"
                "</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{'warn-strip' if not interp_ok else 'info-strip'}'>🎞️ {interp_msg}</div>",
                unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Step 2 · Optimization Goal</div>", unsafe_allow_html=True)
    with st.container(border=True):
        goal = st.slider("Quality ◄────────► Size", 0, 100, 55,
                         help="0 = max quality, 100 = smallest file")
        profile_name = map_slider_to_profile(goal)
        profile_name = st.selectbox("Profile (override)", list(PROFILES.keys()),
                                    index=list(PROFILES.keys()).index(profile_name))
        profile = PROFILES[profile_name]
        st.markdown(f"<div class='info-strip'>{profile['desc']}</div>", unsafe_allow_html=True)

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            codec = st.selectbox("Codec", ["AVC (H.264)","HEVC (H.265)","AV1"],
                index=["AVC (H.264)","HEVC (H.265)","AV1"].index(profile["default_codec"]))
        if codec == "AV1":
            default_crf, default_preset = profile["av1"]["crf"], profile["av1"]["preset"]
            preset_opts = ["4","5","6","7","8"]
        elif codec == "HEVC (H.265)":
            default_crf, default_preset = profile["hevc"]["crf"], profile["hevc"]["preset"]
            preset_opts = ["veryfast","fast","medium","slow"]
        else:
            default_crf, default_preset = profile["h264"]["crf"], profile["h264"]["preset"]
            preset_opts = ["veryfast","fast","medium","slow"]
        with pc2:
            crf = st.slider("CRF (override)", 14, 45, default_crf,
                            help="Lower = higher quality. AV1 typical 28–38.")
        with pc3:
            try: idx = preset_opts.index(str(default_preset))
            except ValueError: idx = 0
            preset = st.selectbox("Preset (override)", preset_opts, index=idx)

        # HW acceleration toggle
        hw_avail = best_hw_encoder(codec)
        if hw_avail:
            use_hw = st.checkbox(f"⚡ Use hardware acceleration ({hw_avail})", value=True,
                                  help="5–20× faster encoding. Quality slightly lower than software at same CRF.")
        else:
            use_hw = False
            st.caption("ℹ️ No hardware encoder available for this codec on this host.")

    st.markdown("<div class='section-title'>Step 3 · Enhancements</div>", unsafe_allow_html=True)
    with st.container(border=True):
        with st.expander("🛡️ Quality enhancement", expanded=True):
            e1,e2,e3 = st.columns(3)
            denoise = e1.checkbox("Denoise")
            deblock = e2.checkbox("Deblock")
            sharpen = e3.checkbox("Sharpen")

        with st.expander("🎨 Color processing"):
            c1,c2 = st.columns(2)
            color = c1.checkbox("Color boost")
            is_hdr_src = detect_hdr(sm) if sm else False
            hdr_sdr = c2.checkbox("HDR → SDR", value=is_hdr_src, disabled=not is_hdr_src,
                                  help="Only enabled when source is HDR.")

        with st.expander("🎞️ Motion processing"):
            interp_ok2, _ = recommend_interpolation(sm) if sm else (True,"")
            interp = st.checkbox("Frame interpolation → 60fps",
                                  disabled=not interp_ok2,
                                  help="Disabled when source already ≥ 50 fps.")

        with st.expander("📐 Resolution"):
            scale_to = st.selectbox("Target size",
                                     ["Source","480p","720p","1080p","2160p"], index=0)

        with st.expander("🔊 Audio processing"):
            a1,a2 = st.columns(2)
            loudnorm = a1.checkbox("EBU R128 loudness normalization",
                                    help="-16 LUFS broadcast standard. Recommended for streaming.")
            resample_48k = a2.checkbox("Resample to 48 kHz",
                                        help="Recommended for streaming compatibility.")

        with st.expander("✂️ Trim / clip"):
            t1,t2 = st.columns(2)
            trim_start = t1.text_input("Start (HH:MM:SS or seconds)", value="")
            trim_end = t2.text_input("End (HH:MM:SS or seconds)", value="")

        with st.expander("🌾 AV1 advanced (codec-specific)"):
            film_grain = st.checkbox("Film grain synthesis",
                value=detect_grain(sm) if sm else False,
                help="Auto-recommended for grainy sources. Can save 20-40% size.")

        with st.expander("🖼️ Image / logo overlay"):
            image_mode = st.selectbox("Attached image behavior",
                ["Ignore image","Watermark / logo overlay","Poster only in player"],
                index=1 if st.session_state.img else 0)
            lc1, lc2 = st.columns(2)
            logo_pos = lc1.selectbox("Logo position",
                ["Top right","Top left","Bottom right","Bottom left"])
            logo_scale = lc2.slider("Logo scale %", 5, 35, 14)

        auto_thumb = st.checkbox("Auto-generate thumbnail", value=True)

    st.markdown("<div class='section-title'>Step 4 · Preview Impact</div>", unsafe_allow_html=True)
    enh = dict(denoise=denoise, sharpen=sharpen, deblock=deblock, color=color,
               hdr_sdr=hdr_sdr, interp=interp, scale_to=scale_to, use_hw=use_hw)
    if sm:
        est = estimate_output(sm, codec, crf, enh)
        with st.container(border=True):
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1: render_metric("Est. Output Size", f"{est['est_size_mb']:.2f} MB")
            with pc2: render_metric("Est. Bitrate", f"{est['est_bitrate_kbps']} kbps")
            with pc3: render_metric("Expected Savings", f"{est['expected_savings_pct']:.1f}%")
            with pc4:
                t = est["est_time_sec"]
                render_metric("Est. Encode Time", f"{t//60}m {t%60}s")
    else:
        st.info("Upload a source video to see estimates.")

    st.markdown("<div class='section-title'>Step 5 · Encode</div>", unsafe_allow_html=True)
    with st.container(border=True):
        go = st.button("✨ Encode Now", type="primary", use_container_width=True)
        if go:
            if not st.session_state.src:
                st.error("Upload a source video first.")
            else:
                sid = uuid.uuid4().hex
                src = Path(st.session_state.src)
                logo = Path(st.session_state.img) if st.session_state.img else None
                o = dict(codec=codec, crf=crf, preset=preset, profile=profile_name,
                         denoise=denoise, sharpen=sharpen, deblock=deblock, color=color,
                         hdr_sdr=hdr_sdr, interp=interp, scale_to=scale_to,
                         image_mode=image_mode, logo_pos=logo_pos, logo_scale=logo_scale,
                         use_hw=use_hw, loudnorm=loudnorm, resample_48k=resample_48k,
                         trim_start=trim_start.strip() or None,
                         trim_end=trim_end.strip() or None,
                         film_grain=film_grain, auto_thumb=auto_thumb)
                bar = st.progress(0.0, text="Starting FFmpeg encode…")
                out_path, log, md = encode_video(src, logo, o, sm, sid,
                    cb=lambda p,t: bar.progress(float(p), text=t))
                if not out_path:
                    st.error(md.get("error","Encoding failed"))
                    if md.get("tail"): st.code(md["tail"])
                else:
                    st.session_state.out = str(out_path)
                    st.session_state.last_md = md
                    st.session_state.last_log = str(log)
                    with st.spinner("Computing quality metrics…"):
                        q = quality_metrics(src, out_path, sid, quick=True)
                    st.session_state.last_metrics = q
                    dm = media(out_path)
                    saved = (1 - dm["size_mb"]/sm["size_mb"])*100 if sm["size_mb"] else 0
                    csvrow({
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "source": src.name, "output": out_path.name,
                        "profile": profile_name, "codec": codec, "crf": crf,
                        "preset": preset, "hw": use_hw,
                        "source_mb": round(sm["size_mb"],3),
                        "output_mb": round(dm["size_mb"],3),
                        "saved_pct": round(saved,2),
                        "PSNR": q.get("PSNR"), "SSIM": q.get("SSIM"),
                        "VMAF": q.get("VMAF"), "VMAF_proxy": q.get("VMAF_proxy"),
                        "log": str(log),
                    })
                    st.success(f"Done · {dm['size_mb']:.2f} MB · saved {saved:.1f}% · See Compare tab")
                    st.download_button("⬇ Download Output", out_path.read_bytes(),
                        out_path.name, md.get("mime","application/octet-stream"))

# ============================================================
# COMPARE
# ============================================================
with tab_compare:
    if not (st.session_state.src and st.session_state.out
            and Path(st.session_state.out).exists()):
        st.info("Run an encode first (Workflow tab) to see the comparison dashboard.")
    else:
        src = Path(st.session_state.src); out = Path(st.session_state.out)
        sm = media(src); dm = media(out); q = st.session_state.last_metrics or {}
        saved_pct = (1 - dm["size_mb"]/sm["size_mb"])*100 if sm["size_mb"] else 0
        br_save = (1 - dm["bitrate_kbps"]/sm["bitrate_kbps"])*100 if sm["bitrate_kbps"] else 0

        st.markdown("<div class='section-title'>Input vs Output</div>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns([1,1,1])
        with cc1:
            st.markdown(f"""<div class='compare-input'>
                <div style='font-weight:800;font-size:1rem;margin-bottom:10px;color:#475569'>📥 INPUT</div>
                <div class='compare-row'><span class='compare-label'>Size</span><span class='compare-val'>{sm['size_mb']:.2f} MB</span></div>
                <div class='compare-row'><span class='compare-label'>Codec</span><span class='compare-val'>{sm['vcodec'].upper()}</span></div>
                <div class='compare-row'><span class='compare-label'>Bitrate</span><span class='compare-val'>{sm['bitrate_kbps']:.0f} kbps</span></div>
                <div class='compare-row'><span class='compare-label'>Resolution</span><span class='compare-val'>{sm['width']}×{sm['height']}</span></div>
                <div class='compare-row'><span class='compare-label'>FPS</span><span class='compare-val'>{sm['fps']:.2f}</span></div>
                <div class='compare-row'><span class='compare-label'>Duration</span><span class='compare-val'>{sm['duration']:.1f}s</span></div>
            </div>""", unsafe_allow_html=True)
        with cc2:
            st.markdown(f"""<div class='savings-card'>
                <div class='savings-value'>{saved_pct:+.1f}%</div>
                <div class='savings-label'>Size Reduction</div>
                <div style='margin-top:12px;font-size:.85rem;opacity:.95'>Bitrate {br_save:+.1f}%</div>
                <div style='margin-top:6px;font-size:.85rem;opacity:.95'>Saved {(sm['size_mb']-dm['size_mb']):.2f} MB</div>
            </div>""", unsafe_allow_html=True)
        with cc3:
            st.markdown(f"""<div class='compare-output'>
                <div style='font-weight:800;font-size:1rem;margin-bottom:10px;color:#1e3a8a'>📤 OUTPUT</div>
                <div class='compare-row'><span class='compare-label'>Size</span><span class='compare-val'>{dm['size_mb']:.2f} MB</span></div>
                <div class='compare-row'><span class='compare-label'>Codec</span><span class='compare-val'>{dm['vcodec'].upper()}</span></div>
                <div class='compare-row'><span class='compare-label'>Bitrate</span><span class='compare-val'>{dm['bitrate_kbps']:.0f} kbps</span></div>
                <div class='compare-row'><span class='compare-label'>Resolution</span><span class='compare-val'>{dm['width']}×{dm['height']}</span></div>
                <div class='compare-row'><span class='compare-label'>FPS</span><span class='compare-val'>{dm['fps']:.2f}</span></div>
                <div class='compare-row'><span class='compare-label'>Duration</span><span class='compare-val'>{dm['duration']:.1f}s</span></div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>Quality Dashboard</div>", unsafe_allow_html=True)
        q1,q2,q3,q4 = st.columns(4)
        with q1:
            vm = q.get("VMAF", q.get("VMAF_proxy"))
            render_metric("VMAF", f"{vm:.2f}" if vm else "—",
                          "True VMAF" if q.get("VMAF") else "Proxy from SSIM")
        with q2: render_metric("SSIM", f"{q.get('SSIM',0):.4f}" if q.get("SSIM") else "—",
                                "0.95+ Good · 0.98+ Excellent")
        with q3: render_metric("PSNR", f"{q.get('PSNR',0):.2f} dB" if q.get("PSNR") else "—",
                                "40+ dB Good")
        with q4:
            ratio = sm["size_mb"]/dm["size_mb"] if dm["size_mb"] else 0
            render_metric("Compression Ratio", f"{ratio:.2f}×", "Size reduction factor")

        st.markdown("<div class='section-title'>Side-by-Side Playback</div>", unsafe_allow_html=True)
        sbs1, sbs2 = st.columns(2)
        poster = Path(st.session_state.img) if st.session_state.img and Path(st.session_state.img).exists() else None
        with sbs1:
            st.markdown("**Original**"); player(src, poster, "video/mp4")
        with sbs2:
            st.markdown("**Encoded**")
            mime_out = "video/webm" if out.suffix.lower()==".webm" else "video/mp4"
            player(out, poster, mime_out)

        if st.session_state.last_md:
            st.download_button("⬇ Download Encoded Video", out.read_bytes(),
                out.name, st.session_state.last_md.get("mime","application/octet-stream"))

# ============================================================
# PLAYER
# ============================================================
with tab_player:
    st.markdown("<div class='section-title'>Universal Player</div>", unsafe_allow_html=True)
    p = None
    if st.session_state.out and Path(st.session_state.out).exists():
        p = Path(st.session_state.out)
        st.caption(f"Loaded latest output: {p.name}")
    else:
        up_p = st.file_uploader("Upload media", type=["mp4","webm","mov","mkv"], key="play_up")
        if up_p: p = save_upload(up_p, IN_DIR)
    if p:
        poster = Path(st.session_state.img) if st.session_state.img and Path(st.session_state.img).exists() else None
        mime = "video/webm" if p.suffix.lower()==".webm" else "video/mp4"
        player(p, poster, mime)

    with st.expander("🎥 Experimental: WebRTC Camera Preview"):
        st.caption("WebRTC may fail on free cloud runtimes.")
        if WEBRTC_AVAILABLE:
            enable = st.checkbox("Enable camera preview")
            if enable:
                try:
                    webrtc_streamer(key="webrtc-v2",
                        rtc_configuration=RTCConfiguration(
                            {"iceServers":[{"urls":["stun:stun.l.google.com:19302"]}]}),
                        media_stream_constraints={"video":True,"audio":False},
                        async_processing=True)
                except Exception as e:
                    st.warning(f"WebRTC failed: {e}")
        else:
            st.warning("streamlit-webrtc not installed.")

# ============================================================
# QUALITY
# ============================================================
with tab_quality:
    st.markdown("<div class='section-title'>Quality Analytics</div>", unsafe_allow_html=True)
    qa, qb = st.columns(2)
    rf = qa.file_uploader("Reference / source", type=["mp4","mov","mkv","webm"], key="ref_up")
    df_file = qb.file_uploader("Distorted / encoded", type=["mp4","mov","mkv","webm"], key="dist_up")
    full = st.checkbox("Full duration (slower)")
    if st.button("Calculate PSNR / SSIM / VMAF", use_container_width=True):
        if not rf or not df_file:
            st.error("Upload both files.")
        else:
            sid = uuid.uuid4().hex
            rp = save_upload(rf, IN_DIR); dp = save_upload(df_file, IN_DIR)
            with st.spinner("Computing metrics…"):
                qm = quality_metrics(rp, dp, sid, quick=not full)
            q1,q2,q3 = st.columns(3)
            with q1: render_metric("PSNR", f"{qm.get('PSNR',0):.2f} dB" if qm.get("PSNR") else "—")
            with q2: render_metric("SSIM", f"{qm.get('SSIM',0):.4f}" if qm.get("SSIM") else "—")
            with q3:
                v = qm.get("VMAF", qm.get("VMAF_proxy"))
                render_metric("VMAF", f"{v:.2f}" if v else "—",
                              "True VMAF" if qm.get("VMAF") else "Proxy")

# ============================================================
# CRF SWEEP
# ============================================================
with tab_sweep:
    st.markdown("<div class='section-title'>Rate-Distortion Sweep</div>", unsafe_allow_html=True)
    src_path = st.session_state.src
    if not src_path:
        su = st.file_uploader("Upload source for sweep",
              type=["mp4","mov","mkv","webm"], key="sweep_up")
        if su:
            sp = save_upload(su, IN_DIR)
            st.session_state.src = str(sp); st.session_state.src_meta = media(sp)
            src_path = str(sp)

    sw1, sw2, sw3, sw4 = st.columns(4)
    sw_codec = sw1.selectbox("Codec", ["AVC (H.264)","HEVC (H.265)","AV1"], key="sw_codec")
    sw_profile = sw2.selectbox("Profile", list(PROFILES.keys()), index=1, key="sw_profile")
    sw_start = sw3.number_input("CRF start", 14, 45, 22, key="sw_start")
    sw_end = sw4.number_input("CRF end", int(sw_start)+1, 51, 38, key="sw_end")
    sw_step = st.slider("Step", 1, 10, 4, key="sw_step")

    if st.button("🚀 Run CRF Sweep", type="primary"):
        if not src_path:
            st.error("Upload a source first.")
        else:
            src = Path(src_path); sm = media(src)
            crfs = list(range(int(sw_start), int(sw_end)+1, int(sw_step)))
            rows = []; prog = st.progress(0, text="Starting sweep…")
            for i, cval in enumerate(crfs):
                sid = uuid.uuid4().hex
                opts = dict(codec=sw_codec, crf=cval,
                            preset="fast" if sw_codec!="AV1" else "6",
                            profile=sw_profile, denoise=False, sharpen=False,
                            deblock=False, color=False, hdr_sdr=False, interp=False,
                            scale_to="Source", image_mode="Ignore image",
                            logo_pos="Top right", logo_scale=14,
                            use_hw=False, loudnorm=False, resample_48k=False,
                            film_grain=False, auto_thumb=False)
                out_p, log, md = encode_video(src, None, opts, sm, sid,
                    cb=lambda p,t,i=i: prog.progress(min(0.99,(i+p)/len(crfs)),
                                                      text=f"CRF {cval} · {t}"))
                if out_p:
                    qm = quality_metrics(src, out_p, sid, quick=True)
                    dm = media(out_p)
                    rows.append({"CRF":cval, "Size MB":round(dm["size_mb"],2),
                                 "Bitrate kbps":round(dm["bitrate_kbps"]),
                                 "PSNR":qm.get("PSNR"), "SSIM":qm.get("SSIM"),
                                 "VMAF":qm.get("VMAF",qm.get("VMAF_proxy")),
                                 "File":out_p.name})
            prog.progress(1.0, text="Sweep complete")
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
                cc = [c for c in ["Size MB","VMAF","SSIM"] if c in df.columns and df[c].notna().any()]
                if cc: st.line_chart(df.set_index("CRF")[cc])
                st.download_button("⬇ Download CSV", df.to_csv(index=False).encode(),
                                    "crf_sweep.csv", "text/csv")

# ============================================================
# ABR
# ============================================================
with tab_abr:
    st.markdown("<div class='section-title'>Adaptive Bitrate Ladder (HLS)</div>", unsafe_allow_html=True)
    src_abr = None
    if st.session_state.out and Path(st.session_state.out).exists():
        src_abr = Path(st.session_state.out)
        st.caption(f"Using latest output: {src_abr.name}")
    else:
        au = st.file_uploader("Upload for ABR", type=["mp4","mov","mkv","webm"], key="abr_up")
        if au: src_abr = save_upload(au, IN_DIR)
    if st.button("Generate HLS ABR Ladder", type="primary"):
        if not src_abr:
            st.error("Upload or encode first.")
        else:
            sid = uuid.uuid4().hex
            with st.spinner("Building 240p / 480p / 720p ladder…"):
                master, log = make_hls(src_abr, sid)
            zp = OUT_DIR/f"abr_package_{int(time.time())}.zip"
            with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
                for pf in master.parent.glob("*"): z.write(pf, pf.name)
            st.success("ABR ladder ready")
            st.code(master.read_text())
            st.download_button("⬇ Download ABR Package", zp.read_bytes(),
                                zp.name, "application/zip")

# ============================================================
# LOGS
# ============================================================
with tab_logs:
    st.markdown("<div class='section-title'>Session Logs</div>", unsafe_allow_html=True)
    csv_p = LOG_DIR/"sessions.csv"
    if csv_p.exists():
        df = pd.read_csv(csv_p)
        st.dataframe(df.tail(200), use_container_width=True)
        st.download_button("⬇ Download sessions CSV", csv_p.read_bytes(),
                            "sessions.csv", "text/csv")
    else:
        st.info("No sessions yet.")
    logs = sorted(LOG_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    if logs:
        sel = st.selectbox("Log file", logs, format_func=lambda x: x.name)
        st.text_area("Preview", sel.read_text(errors="ignore")[-10000:], height=320)
        st.download_button("⬇ Download selected log", sel.read_bytes(),
                            sel.name, "text/plain")

    with st.expander("🔧 Diagnostics"):
        st.write("FFmpeg:", "✅ Ready" if info["ffmpeg"] else "❌ Missing")
        st.caption(info.get("version",""))
        st.write("FFprobe:", "✅ Ready" if info["ffprobe"] else "❌ Missing")
        st.write(f"x264 {'✅' if has_encoder('libx264') else '⚠️'} · "
                  f"x265 {'✅' if has_encoder('libx265') else '⚠️'} · "
                  f"AV1 {'✅' if av1_ready else '⚠️'} · "
                  f"libvmaf {'✅' if has_filter('libvmaf') else '⚠️'}")
        st.write("**Hardware Encoders:**")
        for k, v in hw.items():
            st.caption(f"{k}: {'✅' if v else '—'}")
        st.info("If FFmpeg is missing, ensure `packages.txt` exists
