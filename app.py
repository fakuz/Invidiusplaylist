from flask import Flask, Response
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Servidor IPTV activo en Render"

@app.route('/playlist.m3u')
def generate_playlist():
    try:
        subprocess.run(["python", "generate_playlist.py"], check=True)
        if os.path.exists("playlist.m3u"):
            with open("playlist.m3u", "r", encoding="utf-8") as f:
                content = f.read()
            return Response(content, mimetype="audio/x-mpegurl")
        else:
            return Response("#EXTM3U\n# No se pudo generar la playlist", mimetype="audio/x-mpegurl")
    except Exception as e:
        return f"Error: {str(e)}"