from flask import Flask, Response
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>✅ IPTV Playlist funcionando en /playlist.m3u</h1>"

@app.route("/playlist.m3u")
def playlist():
    try:
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "#EXTM3U\n# No se ha generado la playlist aún."
    return Response(content, mimetype="audio/x-mpegurl")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))