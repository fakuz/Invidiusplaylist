import yt_dlp

INPUT_FILE = "links.txt"
OUTPUT_FILE = "playlist.m3u"

def generar_m3u():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        enlaces = [line.strip() for line in f if line.strip()]

    m3u_lines = ["#EXTM3U"]

    ydl_opts = {
        "format": "best[ext=mp4][height<=1080]",
        "quiet": True,
        "noplaylist": True,
    }

    for link in enlaces:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                url = info["url"]
                title = info.get("title", "Canal")
                m3u_lines.append(f'#EXTINF:-1,{title}')
                m3u_lines.append(url)
                print(f"[OK] {title} agregado")
        except Exception as e:
            print(f"[ERROR] No se pudo procesar {link}: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("\n".join(m3u_lines))

if __name__ == "__main__":
    generar_m3u()