import os
import re
import subprocess
import json
import time
import rookiepy
from datetime import datetime


playlist_file = "playlist.txt" 
cookies_file = "www.youtube.com_cookies.txt" 
output_dir = "downloads" 
biliup_path = "./biliup.exe" 
failed_file = "failed_videos.txt"  
success_file = "success_videos.txt"  


def is_cookie_expired(cookie_file):
    try:
        with open(cookie_file, 'r', encoding='utf-8') as file:
            for line in file:
                
                if line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) > 5:
                    expires = int(parts[4])  
                    if expires > 0 and expires < time.time():
                        return True  
        return False  
    except Exception as e:
        print(f"读取cookie文件失败: {e}")
        return True  

def get_and_save_cookies():
    print("重新获取YouTube Cookies...")
    cookies = rookiepy.chrome(['youtube.com'])
    with open(cookies_file, 'w', encoding='utf-8') as file:
        file.write("# Netscape HTTP Cookie File\n")
        file.write("# This file is generated automatically. Do not edit.\n\n")
        for cookie in cookies:
            domain = cookie['domain']

            if "ssyoutube.com" in domain:
                continue
            if not domain.startswith("."):
                domain = "." + domain
            secure = "TRUE" if cookie['secure'] else "FALSE"
            http_only = "TRUE" if cookie['http_only'] else "FALSE"
            expires = cookie['expires'] if cookie['expires'] else "0"
            path = cookie.get('path', '/')
            name = cookie['name']
            if "GOOGLE_ABUSE_EXEMPTION" == name:
                continue
            value = cookie['value']
            file.write(f"{domain}\t{secure}\t{path}\t{http_only}\t{expires}\t{name}\t{value}\n")
    print("Cookies 已重载")


def extract_video_id(video_url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if match:
        return match.group(1)
    else:
        print(f"无法从链接中提取视频ID: {video_url}")
        return None

def download_video(video_url, video_id):
    print(f"开始下载视频: {video_url}")
    command = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio",
        "--merge-output-format", "mp4",
        "--cookies", cookies_file,
        "--write-info-json",
        "-o", f"{output_dir}/{video_id}.%(ext)s",
        video_url
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:
        print(line.strip())

    process.wait()
    if process.returncode == 0:
        print(f"视频下载成功: {video_url}")
        return True
    else:
        print(f"视频下载失败: {video_url}")
        return False

def read_video_metadata(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            title = data.get("fulltitle", "")
            source = data.get("webpage_url", "")
            description = data.get("description", "")
            description = f"auto donwload&upload by python, huge thanks to yt-dlp & biliup！\n\n{description}"
            return title, source, description
    except Exception as e:
        print(f"读取数据失败: {json_file}, 错误: {e}")
        return "", "", ""

def upload_video(video_path, title, source, description):
    print(f"开始上传视频: {video_path}")
    command = [
        biliup_path,
        "upload",
        "--tid", "171",
        "--copyright", "2",
        "--tag", "bhop,csgo,css",
        "--title", title,
        "--source", source,
        "--desc", description,
        video_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    if result.returncode == 0:
        print(f"视频上传成功: {video_path}")
        return True
    else:
        print(f"视频上传失败: {video_path}\n错误信息:\n{result.stderr}")
        return False

def load_processed_links(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def save_link_to_file(file_path, video_url):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{video_url}\n")

def main():
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(cookies_file) or is_cookie_expired(cookies_file):
        get_and_save_cookies()

    success_links = load_processed_links(success_file)
    failed_links = load_processed_links(failed_file)

    with open(playlist_file, "r", encoding="utf-8") as file:
        video_links = [line.strip() for line in file if line.strip()]

    for video_url in video_links:
        if video_url in success_links:
            print(f"已成功上传，跳过: {video_url}")
            continue

        video_id = extract_video_id(video_url)
        if video_id:
            if download_video(video_url, video_id):
                video_path = os.path.join(output_dir, f"{video_id}.mp4")
                json_path = os.path.join(output_dir, f"{video_id}.info.json")
                title, source, description = read_video_metadata(json_path)
                if upload_video(video_path, title, source, description):
                    save_link_to_file(success_file, video_url)
                else:
                    save_link_to_file(failed_file, video_url)
                os.remove(video_path)
                os.remove(json_path)
                print(f"已删除本地文件: {video_path}, {json_path}")
            else:
                save_link_to_file(failed_file, video_url)

if __name__ == "__main__":
    main()
