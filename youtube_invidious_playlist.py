#!/usr/bin/env python3
import os
import random
import requests
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

INPUT_FILE = "links.txt"
OUTPUT_FILE = "playlist.m3u"
RAW_LINKS_FILE = "raw_links.txt"
MAX_THREADS = os.cpu_count() * 2
INSTANCES_API = "https://api.invidious.io/instances.json?pretty=1"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar.xml"

def get_invidious_instances():
    try:
        resp = requests.get(INSTANCES_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        instances = []
        for item in data:
            if isinstance(item, list) and len(item) >= 2:
                domain = item[0]
                features = item[1]
                if features.get("api", False) and not features.get("dead", False):
                    instances.append(f"https://{domain}")
        return instances
    except Exception as e:
        print(f"[ERROR] No se pudo obtener la lista de instancias: {e}")
        return []

instances = get_invidious_instances()
if not instances:
    print("[ERROR] No hay instancias disponibles de Invidious.")
    sys.exit(1)

if not os.path.exists(INPUT_FILE):
    print(f"[ERROR] No se encontró {INPUT_FILE}.")
    sys.exit(1)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    links = [line.strip() for line in f if line.strip()]

if not links:
    print("[ERROR] El archivo de enlaces está vacío.")
    sys.exit(1)

print(f"[INFO] Procesando {len(links)} enlaces usando {MAX_THREADS} hilos...")

results = []
raw_links = []

def normalize_tvg_id(name):
    nfkd = unicodedata.normalize('NFKD', name)
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return no_accents.lower().replace(" ", "").replace("+", "").replace("&", "")

def extract_video_id(url):
    if "watch?v=" in url:
        return url.split("watch?v=")[-1].split("&")[0]
    return None

def fetch_stream_info(entry):
    try:
        url, category, name = entry.split("|")
    except ValueError:
        return f"[ERROR] Formato incorrecto: {entry}", None

    video_id = extract_video_id(url)
    if not video_id:
        return f"[ERROR] No se pudo extraer ID del video: {url}", None

    instance = random.choice(instances)
    api_url = f"{instance}/api/v1/videos/{video_id}"

    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code != 200:
            return f"[ERROR] {name} -> API error {resp.status_code}", None

        data = resp.json()
        hls_url = data.get("hlsUrl")
        if not hls_url:
            return f"[WARN] {name} -> No tiene HLS disponible (¿no es un live stream?)", None

        thumbnails = data.get("videoThumbnails", [])
        logo = thumbnails[-1]["url"] if thumbnails else ""

        tvg_id = normalize_tvg_id(name)
        m3u_entry = (f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{category}" '
                     f'tvg-logo="{logo}", {name}\n{hls_url}')
        raw_entry = f"{name} | {hls_url}"
        return m3u_entry, raw_entry

    except Exception as e:
        return f"[ERROR] {name} -> {e}", None

with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    future_to_link = {executor.submit(fetch_stream_info, entry): entry for entry in links}
    for future in future_to_link:
        result, raw = future.result()
        if raw:
            results.append(result)
            raw_links.append(raw)
        else:
            print(result)

if results:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n' + "\n".join(results))
    with open(RAW_LINKS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(raw_links))
    print(f"[INFO] Playlist generada: {OUTPUT_FILE} ({len(results)} canales)")
    print(f"[INFO] Enlaces directos guardados en: {RAW_LINKS_FILE}")
else:
    print("[WARN] No se generó contenido. Playlist vacía.")