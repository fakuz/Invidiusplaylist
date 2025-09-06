import yt_dlp
import concurrent.futures

INPUT_FILE = "links.txt"
OUTPUT_FILE = "playlist.m3u"
MAX_THREADS = 4

def get_stream_info(line):
    try:
        url, name = line.strip().split("|")
    except ValueError:
        return None

    ydl_opts = {
        "format": "best[height<=1080][ext=mp4]",
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            for f in info["formats"]:
                if f.get("protocol") == "m3u8_native" and "hls" in f.get("format_note", "").lower():
                    return f'#EXTINF:-1 tvg-logo="{info.get("thumbnail","")}", {name}\n{f["url"]}'
        except Exception as e:
            print(f"[ERROR] {name} -> {e}")
            return None
    return None

def generate_playlist():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("[ERROR] No se encontró links.txt")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = list(executor.map(get_stream_info, links))

    playlist = "#EXTM3U\n" + "\n".join([r for r in results if r])
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist)
    print("[INFO] Playlist generada:", OUTPUT_FILE)

if __name__ == "__main__":
    generate_playlist()