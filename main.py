import os
import sys
import logging
import subprocess
from dotenv import load_dotenv
from webdav3.client import Client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()

NEXTCLOUD_URL = os.getenv("NEXTCLOUD_URL")
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD")
NEXTCLOUD_FOLDER = os.getenv("NEXTCLOUD_FOLDER", "YouTube_Playlists")
PLAYLIST_URLS = os.getenv("PLAYLIST_URLS", "").split(",")
AUDIO_ONLY = os.getenv("AUDIO_ONLY", "false").lower() == "true"

DOWNLOAD_DIR = "/tmp/yt_downloads"
ARCHIVE_FILE = "/app/data/download_history.txt"

def get_webdav_client():
    # Setup WebDAV connection parameters
    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASSWORD
    }
    return Client(options)

def download_playlist(url):
    # Create download folder
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)
    
    # Base yt-dlp command
    cmd = [
        "yt-dlp",
        "--download-archive", ARCHIVE_FILE,
        "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s"
    ]
    
    if AUDIO_ONLY:
        cmd.extend(["-x", "--audio-format", "mp3"])
    else:
        cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
        
    cmd.append(url)
    
    logging.info(f"Processing playlist: {url}")
    subprocess.run(cmd, check=True)

def upload_to_nextcloud():
    # Sync downloaded files to Nextcloud
    client = get_webdav_client()
    
    # Create target directory if missing
    if not client.check(NEXTCLOUD_FOLDER):
        client.mkdir(NEXTCLOUD_FOLDER)

    for filename in os.listdir(DOWNLOAD_DIR):
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.isfile(local_path):
            remote_path = os.path.join(NEXTCLOUD_FOLDER, filename)
            logging.info(f"Uploading {filename}...")
            client.upload_sync(remote_path=remote_path, local_path=local_path)
            os.remove(local_path)

def main():
    # Validate required credentials
    if not NEXTCLOUD_URL or not NEXTCLOUD_USER or not NEXTCLOUD_PASSWORD:
        logging.error("Missing required environment variables in .env file.")
        sys.exit(1)

    for url in PLAYLIST_URLS:
        clean_url = url.strip()
        if not clean_url:
            continue
        try:
            download_playlist(clean_url)
            upload_to_nextcloud()
        except Exception as e:
            logging.error(f"Failed to process {clean_url}: {e}")

if __name__ == "__main__":
    main()