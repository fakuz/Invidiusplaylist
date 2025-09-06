from flask import Flask, Response
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
import os

app = Flask(__name__)
playlist_path = "playlist.m3u"

def generar_playlist():
    print("[INFO] Actualizando playlist...")
    try:
        subprocess.run(["python", "update_playlist.py"], check=True)
        print("[INFO] Playlist actualizada correctamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo actualizar la playlist: {e}")

# Generar la playlist al inicio
generar_playlist()

# Programar actualización cada 30 minutos
scheduler = BackgroundScheduler()
scheduler.add_job(generar_playlist, "interval", minutes=30)
scheduler.start()

@app.route('/')
def home():
    return "✅ IPTV Playlist funcionando en /playlist.m3u"

@app.route('/playlist.m3u')
def playlist():
    if os.path.exists(playlist_path):
        with open(playlist_path, "r", encoding="utf-8") as f:
            data = f.read()
        return Response(data, mimetype="audio/x-mpegurl")
    else:
        return "Playlist no generada aún", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))