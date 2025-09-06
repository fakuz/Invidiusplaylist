from flask import Flask, Response
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>Servidor IPTV activo. Usa /playlist.m3u</h2>"

@app.route("/playlist.m3u")
def playlist():
    result = subprocess.run(['python', 'youtube_to_googlevideo.py'], capture_output=True, text=True)
    return Response(result.stdout, mimetype='audio/x-mpegurl')
