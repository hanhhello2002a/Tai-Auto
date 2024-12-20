import os
import requests
import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
import re
from googleapiclient.discovery import build
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import subprocess
from dotenv import dotenv_values
from io import StringIO
import random
from io import BytesIO

# Đường dẫn đến logo.ico trong thư mục hiện tại
logo_path = os.path.join(os.path.dirname(__file__), "logo.ico")

# Kiểm tra nếu logo chưa tồn tại thì tải từ GitHub
if not os.path.exists(logo_path):
    logo_url = "https://github.com/hanhhello2002a/Tai-Auto/raw/main/logo.ico"
    try:
        response = requests.get(logo_url)
        response.raise_for_status()  # Kiểm tra mã phản hồi HTTP
        with open(logo_path, 'wb') as file:
            file.write(response.content)
        print("Đã tải logo.ico thành công!")
    except requests.exceptions.RequestException as e:
        print(f"Không thể tải logo từ GitHub: {e}")
else:
    print("Logo.ico đã có sẵn trong thư mục.")

def get_youtube_service():
    for api_key in API_KEYS:
        try:
            print(f"Đang sử dụng API Key: {api_key}")
            youtube = build('youtube', 'v3', developerKey=api_key)
            # Gọi thử một API đơn giản để kiểm tra
            youtube.search().list(part="snippet", q="test", maxResults=1).execute()
            return youtube
        except Exception as e:
            print(f"API Key {api_key} không hoạt động: {e}")
    raise Exception("Tất cả API key đều không hoạt động!")


# URL của file .env trên GitHub (thay URL của bạn vào đây)
GITHUB_ENV_URL = "https://raw.githubusercontent.com/hanhhello2002a/Tai-Auto/main/.env"

def load_env_from_github(url):
    try:
        # Lấy nội dung file .env từ GitHub
        response = requests.get(url)
        response.raise_for_status()  # Kiểm tra lỗi khi tải
        env_content = response.text

        # Sử dụng StringIO để tạo file-like object từ chuỗi
        env_variables = dotenv_values(stream=StringIO(env_content))
        
        # Nạp nội dung file .env vào môi trường
        for key, value in env_variables.items():
            os.environ[key] = value  # Đặt biến môi trường
        print("Đã tải và nạp .env từ GitHub thành công!")
    except Exception as e:
        print(f"Lỗi khi tải file .env từ GitHub: {e}")

# Gọi hàm để tải và nạp file .env
load_env_from_github(GITHUB_ENV_URL)

# Sử dụng API_KEYS từ file .env
API_KEYS = os.getenv("API_KEYS").split(',')
print("API_KEYS:", API_KEYS)

def get_channel_id_from_handle(handle):
    try:
        youtube = get_youtube_service()
        response = youtube.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=1
        ).execute()
        channel_id = response['items'][0]['id']['channelId']
        return channel_id
    except Exception as e:
        print(f"Không thể lấy ID từ handle: {e}")
        return None


def get_available_formats(video_url):
    try:
        with yt_dlp.YoutubeDL({'listformats': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            print("Các định dạng có sẵn:")
            for format in info['formats']:
                print(f"{format['format_id']}: {format['ext']} {format.get('resolution', 'N/A')}")
    except Exception as e:
        print(f"Lỗi khi kiểm tra định dạng: {e}")

def get_video_details(video_id):
    youtube = get_youtube_service()
    try:
        request = youtube.videos().list(part='snippet', id=video_id)
        response = request.execute()
        if 'items' in response and len(response['items']) > 0:
            title = response['items'][0]['snippet']['title']
            return title
    except Exception as e:
        print(f"Không thể lấy thông tin video: {e}")
    return None

def get_videos_from_channel(channel_id, order="date"):
    youtube = get_youtube_service()
    video_ids = []
    try:
        request = youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=50,
            order=order,
            type="video"
        )
        response = request.execute()
        while response and 'items' in response:
            for item in response['items']:
                video_ids.append(item['id']['videoId'])
            request = youtube.search().list_next(request, response)
            response = request.execute() if request else None
    except Exception as e:
        print(f"Không thể lấy video từ kênh: {e}")
    return video_ids

def get_videos_from_playlist(playlist_id):
    youtube = get_youtube_service()
    video_ids = []
    try:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50
        )
        response = request.execute()
        while response and 'items' in response:
            for item in response['items']:
                video_ids.append(item['snippet']['resourceId']['videoId'])
            request = youtube.playlistItems().list_next(request, response)
            response = request.execute() if request else None
    except Exception as e:
        print(f"Không thể lấy video từ danh sách phát: {e}")
    return video_ids

def download_thumbnail(video_id, save_path):
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    response = requests.get(thumbnail_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"Tải thumbnail thành công: {save_path}")
    else:
        print(f"Không thể tải thumbnail từ {thumbnail_url}.")

def download_video(url, video_path, thumbnail_path, download_thumbnail_flag, order_number, title):
    ydl_opts = {
    'outtmpl': os.path.join(video_path, f"{order_number}-{title}.%(ext)s"),
    'format': '720[ext=mp4][vcodec=h264]+bestaudio[ext=m4a]/best',
    'merge_output_format': 'mp4',
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',  # Chuyển đổi sang định dạng mp4 nếu cần thiết
    }],
}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"Tải video thành công: {info['title']}")
            if download_thumbnail_flag:
                download_thumbnail(info['id'], os.path.join(thumbnail_path, f"{order_number}-{title}.png"))
    except Exception as e:
        print(f"Có lỗi xảy ra trong quá trình tải video: {e}")

def extract_id(url):
    channel_regex = r'channel/([a-zA-Z0-9_-]+)'
    playlist_regex = r'list=([a-zA-Z0-9_-]+)'
    handle_regex = r'@([a-zA-Z0-9_-]+)'

    channel_match = re.search(channel_regex, url)
    playlist_match = re.search(playlist_regex, url)
    handle_match = re.search(handle_regex, url)

    if channel_match:
        return 'channel', channel_match.group(1)
    elif playlist_match:
        return 'playlist', playlist_match.group(1)
    elif handle_match:
        return 'handle', handle_match.group(1)
    else:
        print("URL không hợp lệ hoặc không phải kênh/danh sách phát.")
        return None, None

def start_download():
    urls = url_entry.get().split(',')
    save_dir = output_dir_entry.get()

    if not os.path.isdir(save_dir):
        messagebox.showerror("Lỗi", "Đường dẫn lưu không hợp lệ!")
        return

    video_path = os.path.join(save_dir, "Video")
    thumbnail_path = os.path.join(save_dir, "Thumbnail")
    os.makedirs(video_path, exist_ok=True)
    os.makedirs(thumbnail_path, exist_ok=True)

    mode = mode_combobox.get()
    sort_order = sort_combobox.get()
    order_mapping = {"Mới nhất": "date", "Phổ biến": "viewCount", "Cũ nhất": "relevance"}
    order_number = 1

    tasks = []

    with ThreadPoolExecutor(max_workers=int(thread_spinbox.get())) as executor:
        for url in urls:
            url_type, extracted_id = extract_id(url.strip())
            if url_type == 'channel':
                video_ids = get_videos_from_channel(extracted_id, order_mapping[sort_order])
            elif url_type == 'playlist':
                video_ids = get_videos_from_playlist(extracted_id)
            elif url_type == 'handle':
                channel_id = get_channel_id_from_handle(extracted_id)
                if channel_id:
                    video_ids = get_videos_from_channel(channel_id, order_mapping[sort_order])
                else:
                    messagebox.showwarning("Cảnh báo", f"Không thể lấy ID từ handle: {url}")
                    continue
            else:
                messagebox.showwarning("Cảnh báo", f"URL không hợp lệ: {url}")
                continue

            for video_id in video_ids:
                title = get_video_details(video_id)
                if title:
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    if mode == "Chỉ Thumbnail":
                        executor.submit(download_thumbnail, video_id, os.path.join(thumbnail_path, f"{order_number}-{safe_title}.png"))
                    elif mode in ["Video và Thumbnail", "Chỉ Video"]:
                        executor.submit(
                            download_video,
                            f'https://www.youtube.com/watch?v={video_id}',
                            video_path,
                            thumbnail_path,
                            mode == "Video và Thumbnail",
                            order_number,
                            safe_title,
                        )
                    order_number += 1
                    
# Hàm đổi màu khi di chuột vào nút
def on_hover(event, button, hover_bg="#1ABC9C", hover_fg="white"):
    button.config(bg=hover_bg, fg=hover_fg)

def on_leave(event, button, default_bg="#2C3E50", default_fg="white"):
    button.config(bg=default_bg, fg=default_fg)       
    button.config(bg=default_bg, fg=default_fg)   

def show_start_message():
    # Tạo một label cho thông báo "Bắt đầu tải"
    start_label = tk.Label(root, text="Bắt đầu tải...", fg="green", font=("Arial", 12))
    start_label.place(x=10, y=220)  # Đặt ở góc trái, dưới cùng giao diện
    # Sau 3 giây, ẩn label
    root.after(3000, start_label.destroy)    

# Giao diện
root = tk.Tk()
root.title("Tải Video YouTube")
root.geometry("500x200")
# Không cho phép thay đổi kích thước cửa sổ
root.resizable(False, False)

title_frame = tk.Frame(root, bg="#2C3E50")
title_frame.pack(fill=tk.X)

input_frame = tk.Frame(root)
input_frame.pack(pady=10)

url_label = tk.Label(input_frame, text="Nhập URL: ")
url_label.grid(row=0, column=0, padx=5)

url_entry = tk.Entry(input_frame, width=54)
url_entry.grid(row=0, column=1, padx=5)

def paste_url():
    try:
        url = root.clipboard_get()
        url_entry.insert(tk.END, url)
    except tk.TclError:
        messagebox.showwarning("Cảnh báo", "Clipboard không có dữ liệu.")

paste_button = tk.Button(input_frame, text="📄 Dán URL", command=paste_url)
paste_button.grid(row=0, column=2, padx=5)

output_label = tk.Label(input_frame, text="Chọn ổ lưu: ")
output_label.grid(row=1, column=0, padx=5)

output_dir_entry = tk.Entry(input_frame, width=54)
output_dir_entry.grid(row=1, column=1, padx=5)

def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        output_dir_entry.delete(0, tk.END)
        output_dir_entry.insert(0, folder_selected)

browse_button = tk.Button(input_frame, text="🔍 Duyệt.....", command=browse_folder)
browse_button.grid(row=1, column=2, padx=5)

mode_frame = tk.Frame(root)
mode_frame.pack(pady=10)

mode_label = tk.Label(mode_frame, text="Chọn chế độ tải: ")
mode_label.pack(side=tk.LEFT, padx=5)

mode_combobox = ttk.Combobox(mode_frame, values=["Chỉ Video", "Chỉ Thumbnail", "Video và Thumbnail"], state='readonly',width=17)
mode_combobox.set("Video và Thumbnail")
mode_combobox.pack(side=tk.LEFT, padx=5)

sort_label = tk.Label(mode_frame, text="Sắp xếp: ")
sort_label.pack(side=tk.LEFT, padx=5)

sort_combobox = ttk.Combobox(mode_frame, values=["Mới nhất", "Phổ biến", "Cũ nhất"], state='readonly',width=8)
sort_combobox.set("Mới nhất")
sort_combobox.pack(side=tk.LEFT, padx=5)

# Thêm Label cho số luồng
thread_label = tk.Label(mode_frame, text="Số luồng: ")
thread_label.pack(side=tk.LEFT, padx=5)

# Tạo Spinbox cho số luồng
thread_spinbox = tk.Spinbox(mode_frame, from_=1, to=50, width=5)
thread_spinbox.delete(0, tk.END)
thread_spinbox.insert(0, "5")  # Số luồng mặc định
thread_spinbox.pack(side=tk.LEFT, padx=5)

download_button = tk.Button(root, text=" 🕹 Bắt đầu tải", command=lambda: [show_start_message(), threading.Thread(target=start_download, daemon=True).start()])
download_button.pack(pady=10)

# Thêm thông tin phát triển
credit_frame = tk.Frame(root, bg="#2C3E50")  # Tạo khung cho thông tin
credit_frame.pack(side=tk.BOTTOM, fill=tk.X)  # Đặt khung ở dưới cùng

# Thêm liên kết Facebook
facebook_link = tk.Label(credit_frame, text="Hanh Hello", bg="#FFFF00", fg="blue", cursor="hand2", font=("Arial", 12, "bold"))
facebook_link.pack(side=tk.RIGHT)  # Đặt liên kết bên cạnh nhãn phát triển
facebook_link.bind("<Button-1>", lambda e: subprocess.Popen(['start', 'https://www.facebook.com/profile.php?id=61557954673943'], shell=True))

# Tăng cỡ chữ của nhãn phát triển
credit_label = tk.Label(credit_frame, text='Phát triển bởi ', bg="#2C3E50", fg="white", font=("Arial", 14, "bold"))
credit_label.pack(side=tk.RIGHT, padx=(0, 10))  # Đặt nhãn ở bên phải

# Thêm logo làm biểu tượng cửa sổ
root.iconbitmap(logo_path)


# Tùy chỉnh màu cho từng nút
paste_button.bind("<Enter>", lambda e: on_hover(e, paste_button, hover_bg="#3498DB", hover_fg="white"))  # Xanh dương
paste_button.bind("<Leave>", lambda e: on_leave(e, paste_button, default_bg="#E8F6F3", default_fg="black"))

browse_button.bind("<Enter>", lambda e: on_hover(e, browse_button, hover_bg="#3498DB", hover_fg="white"))  # Cam nhạt
browse_button.bind("<Leave>", lambda e: on_leave(e, browse_button, default_bg="#E8F6F3", default_fg="black"))

download_button.bind("<Enter>", lambda e: on_hover(e, download_button, hover_bg="#E74C3C", hover_fg="white"))  # Đỏ
download_button.bind("<Leave>", lambda e: on_leave(e, download_button, default_bg="#2ECC71", default_fg="white"))  # Xanh lá

# Cấu hình mặc định ban đầu
paste_button.config(bg="#E8F6F3", fg="black")
browse_button.config(bg="#E8F6F3", fg="black")
download_button.config(bg="#2ECC71", fg="white")

root.mainloop()
