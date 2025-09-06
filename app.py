from flask import Flask, Response
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Servidor IPTV funcionando en Render", 200

@app.route('/playlist.m3u')
def playlist():
    if not os.path.exists('links.txt'):
        return "Archivo links.txt no encontrado", 404

    with open('links.txt', 'r') as f:
        lines = f.readlines()

    playlist = "#EXTM3U\n"
    for line in lines:
        line = line.strip()
        if line:
            url, name = line.split('|')[0], line.split('|')[-1]
            playlist += f"#EXTINF:-1,{name}\n{url}\n"

    return Response(playlist, mimetype='audio/mpegurl')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))