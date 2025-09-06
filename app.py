import os
import requests
import concurrent.futures
from flask import Flask, send_file
from apscheduler.schedulers.background import BackgroundScheduler

# Configuración
PLAYLIST_FILE = "playlist.m3u"
LINKS_FILE = "links.txt"
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.syncpundit.com"
]

app = Flask(__name__)

# Función para obtener streams desde Piped
def get_stream_from_piped(video_id):
    for instance in PIPED_INSTANCES:
        try:
            url = f"{instance}/streams/{video_id}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                streams = data.get("videoStreams", [])
                if streams:
                    best_stream = sorted(streams, key=lambda x: int(x["height"]), reverse=True)[0]
                    return best_stream["url"]
        except Exception as e:
            print(f"[ERROR] {video_id} -> {e}")
    return None

# Generador de playlist
def generate_playlist():
    print("[INFO] Generando playlist...")
    if not os.path.exists(LINKS_FILE):
        print("[ERROR] No existe links.txt")
        return

    with open(LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("[WARN] No hay enlaces en links.txt")
        return

    playlist_content = "#EXTM3U\n"
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_link = {executor.submit(process_link, link): link for link in links}
        for future in concurrent.futures.as_completed(future_to_link):
            result = future.result()
            if result:
                results.append(result)

    for item in results:
        playlist_content += f"#EXTINF:-1,{item['title']}\n{item['url']}\n"

    with open(PLAYLIST_FILE, "w") as f:
        f.write(playlist_content)

    print(f"[INFO] Playlist generada con {len(results)} canales.")

def process_link(line):
    try:
        parts = line.split("|")
        url = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else "Canal"
        video_id = url.split("v=")[-1].split("&")[0]
        stream_url = get_stream_from_piped(video_id)
        if stream_url:
            return {"title": title, "url": stream_url}
    except Exception as e:
        print(f"[ERROR] {line} -> {e}")
    return None

# Inicializar scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(generate_playlist, "interval", minutes=30)
scheduler.start()

# Rutas Flask
@app.route("/")
def home():
    return "<h2>Servidor IPTV activo</h2><p>Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/playlist.m3u")
def get_playlist():
    if os.path.exists(PLAYLIST_FILE):
        return send_file(PLAYLIST_FILE, mimetype="audio/x-mpegurl")
    else:
        return "Playlist no disponible", 404

if __name__ == "__main__":
    generate_playlist()  # Generar al inicio
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))