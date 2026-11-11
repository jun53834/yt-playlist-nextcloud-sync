import os
import sys
import shutil
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
    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASSWORD
    }
    return Client(options)

def download_playlist(url):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)
    
    # yt-dlp flags for playlist folders, metadata, and embedded cover art
    cmd = [
        "yt-dlp",
        "--download-archive", ARCHIVE_FILE,
        "--embed-metadata",
        "--embed-thumbnail",
        "--convert-thumbnails", "jpg",
        "-o", f"{DOWNLOAD_DIR}/%(playlist_title,playlist|Playlists)s/%(title)s.%(ext)s"
    ]
    
    if AUDIO_ONLY:
        cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
    else:
        cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
        
    cmd.append(url)
    
    logging.info(f"Processing playlist: {url}")
    subprocess.run(cmd, check=True)

def upload_to_nextcloud():
    client = get_webdav_client()
    
    if not client.check(NEXTCLOUD_FOLDER):
        client.mkdir(NEXTCLOUD_FOLDER)

    # Recursively upload directory tree to Nextcloud
    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        for filename in files:
            local_path = os.path.join(root, filename)
            rel_path = os.path.relpath(local_path, DOWNLOAD_DIR)
            remote_path = os.path.join(NEXTCLOUD_FOLDER, rel_path).replace("\\", "/")
            
            # Ensure remote target directory structure exists on Nextcloud
            remote_dir = os.path.dirname(remote_path)
            parts = remote_dir.strip('/').split('/')
            current_path = ""
            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part
                if not client.check(current_path):
                    client.mkdir(current_path)
                        
            logging.info(f"Uploading {rel_path}...")
            client.upload_sync(remote_path=remote_path, local_path=local_path)

    # Clean up local download directory after successful upload
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)

def main():
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