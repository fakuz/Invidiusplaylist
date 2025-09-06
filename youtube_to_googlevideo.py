import yt_dlp
import sys

INPUT_FILE = "links.txt"

def get_stream(url):
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'geo_bypass': True,
        'skip_download': True,
        'nocheckcertificate': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url")
    except Exception as e:
        print(f"# ERROR obteniendo stream: {e}", file=sys.stderr)
        return None

def generate_playlist():
    output = "#EXTM3U\n"
    with open(INPUT_FILE, "r") as f:
        for line in f:
            if "," in line:
                name, url = line.strip().split(",", 1)
                stream_url = get_stream(url)
                if stream_url:
                    output += f'#EXTINF:-1,{name}\n{stream_url}\n'
    return output

if __name__ == "__main__":
    print(generate_playlist())