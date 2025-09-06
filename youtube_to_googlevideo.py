#!/usr/bin/env python3
import requests
import concurrent.futures
import os

# ============ CONFIG ==============
INPUT_FILE = "links.txt"
OUTPUT_FILE = "playlist.m3u"
RAW_LINKS_FILE = "raw_links.txt"
THREADS = os.cpu_count() * 2  # Hiperthreading
EPG_URLS = "https://iptv-org.github.io/epg/guides/ar.xml,https://iptv-org.github.io/epg/guides/es.xml"

# Instancias Piped
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.syncpundit.io",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.jae.fi"
]

# =================================

def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None

def fetch_stream(video_id):
    for instance in PIPED_INSTANCES:
        try:
            api_url = f"{instance}/streams/{video_id}"
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Buscar HLS
                if data.get("hls"):
                    return data["title"], data.get("uploader"), data["hls"], data.get("thumbnailUrl")
                # Fallback: mejor videoStream (1080p si existe)
                streams = data.get("videoStreams", [])
                if streams:
                    best = sorted(streams, key=lambda x: x.get("quality", ""), reverse=True)[0]
                    return data["title"], data.get("uploader"), best["url"], data.get("thumbnailUrl")
        except Exception as e:
            continue
    return None

def process_link(line):
    parts = line.strip().split("|")
    if len(parts) < 3:
        return None
    url, category, name = parts
    video_id = get_video_id(url)
    if not video_id:
        return None
    result = fetch_stream(video_id)
    if result:
        title, uploader, stream_url, logo = result
        return {
            "name": name,
            "category": category,
            "title": title,
            "uploader": uploader,
            "stream": stream_url,
            "logo": logo
        }
    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print("[ERROR] No se encontró links.txt")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        links = [l.strip() for l in f if l.strip()]

    print(f"[INFO] Procesando {len(links)} enlaces usando {THREADS} hilos...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for res in executor.map(process_link, links):
            if res:
                results.append(res)

    if not results:
        print("[WARN] No se generó contenido. Playlist vacía.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as m3u, open(RAW_LINKS_FILE, "w", encoding="utf-8") as raw:
        m3u.write(f'#EXTM3U url-tvg="{EPG_URLS}"\n')
        for item in results:
            m3u.write(f'#EXTINF:-1 group-title="{item["category"]}" tvg-logo="{item["logo"]}", {item["name"]}\n')
            m3u.write(f'{item["stream"]}\n')
            raw.write(f'{item["stream"]}\n')

    print(f"[OK] Playlist generada: {OUTPUT_FILE}")
    print(f"[OK] Enlaces directos guardados en: {RAW_LINKS_FILE}")

if __name__ == "__main__":
    main()