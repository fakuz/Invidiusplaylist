import yt_dlp

INPUT_FILE = "links.txt"
OUTPUT_FILE = "playlist.m3u"

def obtener_url_directa(video_url):
    try:
        ydl_opts = {
            'format': 'best[height<=1080][ext=mp4]/best',  # Mejor calidad hasta 1080p
            'quiet': True,
            'skip_download': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
    except Exception as e:
        print(f"[ERROR] {video_url}: {str(e)}")
        return None

def generar_playlist():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("#EXTM3U\n")
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                url = parts[0]
                nombre = parts[1] if len(parts) > 1 else "Canal"
                direct_url = obtener_url_directa(url)
                if direct_url:
                    out.write(f'#EXTINF:-1,{nombre}\n{direct_url}\n')
                else:
                    print(f"[WARN] No se pudo procesar: {url}")

if __name__ == "__main__":
    print("[INFO] Generando playlist...")
    generar_playlist()
    print("[INFO] Playlist generada:", OUTPUT_FILE)