import os
import httpx
from flask import Flask, Response
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Configuración
PIPE_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.in.projectsegfau.lt"
]
THREADS = 8
TIMEOUT = 15
QUALITY = "1080p"  # Mejor calidad disponible
PLAYLIST_FILE = "playlist.m3u"
LINKS_FILE = "links.txt"

def fetch_stream(video_id):
    for instance in PIPE_INSTANCES:
        try:
            url = f"{instance}/streams/{video_id}"
            headers = {"User-Agent": "Mozilla/5.0"}
            with httpx.Client(headers=headers, timeout=TIMEOUT, http2=True) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    streams = data.get("videoStreams", [])
                    if streams:
                        # Buscar la mejor calidad posible (1080p si está disponible)
                        sorted_streams = sorted(streams, key=lambda x: int(x.get("quality", "0p")[:-1]), reverse=True)
                        for stream in sorted_streams:
                            if QUALITY in stream["quality"] or "1080" in stream["quality"]:
                                return stream["url"]
                        return sorted_streams[0]["url"]  # Si no hay 1080p, usar la mejor disponible
        except Exception as e:
            print(f"[ERR] {video_id} -> {instance} fallo ({e})")
    return None

def build_playlist():
    if not os.path.exists(LINKS_FILE):
        return "#EXTM3U\n"

    playlist = "#EXTM3U\n"
    links = open(LINKS_FILE, "r", encoding="utf-8").read().splitlines()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        results = executor.map(process_line, links)

    for entry in results:
        if entry:
            playlist += entry

    return playlist

def process_line(line):
    parts = line.strip().split("|")
    if len(parts) < 2:
        return None
    url, name = parts[0], parts[1]
    if "youtube.com" in url and "watch?v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]
        stream_url = fetch_stream(video_id)
        if stream_url:
            return f'#EXTINF:-1 tvg-name="{name}",{name}\n{stream_url}\n'
    return None

@app.route("/")
def home():
    return "<h1>Servidor IPTV activo</h1><p>Accede a <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/playlist.m3u")
def playlist():
    content = build_playlist()
    return Response(content, mimetype="audio/x-mpegurl")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))