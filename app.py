import os, re, time, threading, json, datetime
from pathlib import Path
from typing import List, Tuple, Optional
import httpx
from flask import Flask, Response, send_file, jsonify, request, abort

# ====== Config ======
LINKS_FILE      = os.getenv("LINKS_FILE", "links.txt")
PLAYLIST_PATH   = Path(os.getenv("PLAYLIST_PATH", "/tmp/playlist.m3u"))
REFRESH_MINUTES = int(os.getenv("REFRESH_MINUTES", "180"))  # 3 horas
PIPE_TIMEOUT    = int(os.getenv("PIPE_TIMEOUT", "12"))
PIPE_TRIES      = int(os.getenv("PIPE_TRIES", "3"))
FORCE_TOKEN     = os.getenv("FORCE_TOKEN")  # opcional para /force-rebuild

# Instancias Piped (se prueban en orden, con reintentos)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.in.projectsegfau.lt",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.syncpundit.io",
    "https://pipedapi.garudalinux.org",
]

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"

app = Flask(__name__)

# ====== Utilidades ======
YT_ID_RE = re.compile(
    r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?#]|$)"
)

def now_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def log(msg: str):
    print(f"[{now_iso()}] {msg}", flush=True)

def extract_video_id(url: str) -> Optional[str]:
    # Soporta https://www.youtube.com/watch?v=ID y https://youtu.be/ID
    m = YT_ID_RE.search(url)
    return m.group(1) if m else None

def parse_links_file(path: str) -> List[Tuple[str, str]]:
    """
    Devuelve lista de (video_id, nombre).
    Acepta:
      URL|Nombre
      URL|Categoria|Nombre  (la categoría se ignora)
    Lineas vacías o que empiezan con # se omiten.
    """
    items = []
    p = Path(path)
    if not p.exists():
        log(f"[WARN] {path} no existe.")
        return items
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [s.strip() for s in line.split("|")]
        if len(parts) == 2:
            url, name = parts
        elif len(parts) >= 3:
            url, _cat, name = parts[0], parts[1], parts[2]
        else:
            url, name = parts[0], parts[0]
        vid = extract_video_id(url)
        if not vid:
            log(f"[WARN] No pude extraer ID de: {url}")
            continue
        items.append((vid, name))
    return items

def fetch_stream_from_piped(video_id: str) -> Optional[str]:
    """
    Intenta obtener una URL reproducible para M3U.
    Preferencia: HLS (hls) cuando está disponible (más estable para live).
    Fallback: formatStreams/videoStreams -> url (googlevideo).
    """
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
    }
    for base in PIPED_INSTANCES:
        url = f"{base}/streams/{video_id}"
        for attempt in range(1, PIPE_TRIES + 1):
            try:
                with httpx.Client(headers=headers, timeout=PIPE_TIMEOUT, http2=True) as client:
                    r = client.get(url)
                    if r.status_code == 403:
                        log(f"[PIPED 403] {video_id} en {base} intento {attempt}")
                        continue
                    r.raise_for_status()
                    data = r.json()
                    # 1) HLS si existe (para directos suele venir aquí)
                    hls = data.get("hls")
                    if hls:
                        return hls
                    # 2) formatStreams (progresivos)
                    fs = data.get("formatStreams") or []
                    for s in fs:
                        if s.get("url"):
                            return s["url"]
                    # 3) videoStreams (segmentados)
                    vs = data.get("videoStreams") or []
                    for s in vs:
                        if s.get("url"):
                            return s["url"]
                    log(f"[PIPED] Sin URLs útiles para {video_id} en {base}")
                    break
            except Exception as e:
                log(f"[ERR] {video_id} -> {base} fallo ({e}) intento {attempt}")
                # reintenta misma instancia
                continue
        # siguiente instancia
    return None

def build_m3u(pairs: List[Tuple[str, str]]) -> str:
    """
    Genera contenido M3U. Intenta resolver cada ID con Piped.
    Solo incluye las entradas con URL válida.
    """
    lines = ["#EXTM3U"]
    ok = 0
    for vid, name in pairs:
        stream = fetch_stream_from_piped(vid)
        if not stream:
            log(f"[SKIP] No stream para {name} ({vid})")
            continue
        # EXTINF -1 para live canales
        lines.append(f'#EXTINF:-1 tvg-name="{name}",{name}')
        lines.append(stream)
        ok += 1
    log(f"[M3U] Entradas válidas: {ok}/{len(pairs)}")
    return "\n".join(lines) + "\n"

def write_playlist(text: str):
    PLAYLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAYLIST_PATH.write_text(text, encoding="utf-8")
    log(f"[M3U] Escrito en {PLAYLIST_PATH}")

def generate_and_save() -> bool:
    pairs = parse_links_file(LINKS_FILE)
    if not pairs:
        log("[WARN] links.txt vacío o no válido.")
        # aún así escribimos cabecera para no dar 404
        write_playlist("#EXTM3U\n")
        return False
    m3u = build_m3u(pairs)
    write_playlist(m3u)
    return True

def auto_refresher_loop():
    # Genera al arrancar
    try:
        log("[JOB] Generando playlist inicial…")
        generate_and_save()
    except Exception as e:
        log(f"[JOB] Error inicial: {e}")
    # Luego cada N minutos
    interval = max(5, REFRESH_MINUTES) * 60
    while True:
        time.sleep(interval)
        try:
            log("[JOB] Regenerando playlist programada…")
            generate_and_save()
        except Exception as e:
            log(f"[JOB] Error regenerando: {e}")

# ====== Rutas ======
@app.route("/")
def root():
    return jsonify({
        "status": "ok",
        "playlist": "/playlist.m3u",
        "updated": PLAYLIST_PATH.stat().st_mtime if PLAYLIST_PATH.exists() else None
    })

@app.route("/playlist.m3u")
def playlist():
    # Si no existe o está muy vieja, intenta refrescar sin bloquear demasiado
    try:
        need_rebuild = True
        if PLAYLIST_PATH.exists():
            age = time.time() - PLAYLIST_PATH.stat().st_mtime
            need_rebuild = age > (REFRESH_MINUTES * 60)
        if need_rebuild and request.args.get("sync") == "1":
            log("[HTTP] Rebuild síncrono solicitado")
            generate_and_save()
    except Exception as e:
        log(f"[HTTP] Error revisando/regen: {e}")

    if not PLAYLIST_PATH.exists():
        # Último recurso: generar rápido
        log("[HTTP] playlist no existe, generando de emergencia…")
        try:
            generate_and_save()
        except Exception as e:
            log(f"[HTTP] Falla generando: {e}")
            return Response("#EXTM3U\n", mimetype="audio/x-mpegurl")

    resp = send_file(str(PLAYLIST_PATH), mimetype="audio/x-mpegurl", as_attachment=False, download_name="playlist.m3u")
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp

@app.route("/force-rebuild", methods=["POST", "GET"])
def force_rebuild():
    if FORCE_TOKEN:
        token = request.args.get("token") or request.headers.get("X-Token")
        if token != FORCE_TOKEN:
            abort(401)
    ok = generate_and_save()
    return jsonify({"ok": ok, "time": now_iso()})

@app.route("/healthz")
def health():
    return "ok"

# ====== Inicio del background loop ======
def _start_bg():
    t = threading.Thread(target=auto_refresher_loop, daemon=True)
    t.start()

_start_bg()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)