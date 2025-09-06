import requests
import concurrent.futures
import time
import os

# ==================== CONFIG ====================
INPUT_FILE = "links.txt"
OUTPUT_FILE = "playlist.m3u"
RAW_LINKS_FILE = "raw_links.txt"
MAX_WORKERS = 8  # Hiperthreading activado
TIMEOUT = 12
MAX_RETRIES = 3

# Instancias Piped (ordenadas por estabilidad)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.syncpundit.io",
    "https://pipedapi.garudalinux.org",
    "https://pipedapi.in.projectsegfau.lt",
]

# EPG recomendado
EPG_URLS = [
    "https://iptv-org.github.io/epg/guides/ar.xml",
    "https://iptv-org.github.io/epg/guides/es.xml"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
}

# ==================== FUNCIONES ====================
def obtener_info(video_id):
    """Intenta obtener info del video desde varias instancias Piped."""
    for instancia in PIPED_INSTANCES:
        url = f"{instancia}/streams/{video_id}"
        for intento in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    if "hls" in data and data["hls"]:
                        return {
                            "title": data.get("title", "Sin título"),
                            "thumbnail": data.get("thumbnailUrl", ""),
                            "hls": data["hls"]
                        }
                    else:
                        print(f"[WARN] {video_id} sin HLS en {instancia}")
                        break
                else:
                    print(f"[ERROR] {video_id} -> HTTP {resp.status_code} en {instancia} (intento {intento})")
            except Exception as e:
                print(f"[ERROR] {video_id} -> {instancia} fallo ({e}) intento {intento}")
            time.sleep(1)
    return None

def procesar_linea(linea):
    """Procesa cada línea del archivo links.txt"""
    try:
        url, categoria, nombre = linea.strip().split("|")
        video_id = url.split("v=")[-1]
        info = obtener_info(video_id)
        if info:
            return f'#EXTINF:-1 group-title="{categoria}" tvg-logo="{info["thumbnail"]}", {nombre}\n{info["hls"]}\n', info["hls"]
        else:
            print(f"[ERROR] {nombre} -> Todas las instancias fallaron")
    except Exception as e:
        print(f"[ERROR] Línea inválida: {linea} ({e})")
    return None

# ==================== MAIN ====================
if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] No se encontró {INPUT_FILE}")
        exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    print(f"[INFO] Procesando {len(links)} enlaces usando {MAX_WORKERS} hilos...")

    playlist = [f'#EXTM3U url-tvg="{",".join(EPG_URLS)}"\n']
    raw_links = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        resultados = executor.map(procesar_linea, links)

    for resultado in resultados:
        if resultado:
            extinf, raw = resultado
            playlist.append(extinf)
            raw_links.append(raw)

    if len(playlist) > 1:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.writelines(playlist)
        with open(RAW_LINKS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(raw_links))
        print(f"[OK] Playlist generada con {len(raw_links)} canales -> {OUTPUT_FILE}")
    else:
        print("[WARN] No se generó contenido. Playlist vacía.")