import os
from pathlib import Path
from datetime import timedelta

def format_timestamp(seconds: float) -> str:
    """Chuyển số giây thành định dạng SRT: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    ms = int((seconds - int(seconds)) * 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"

def safe_remove(path: Path):
    """Xoá file nếu tồn tại"""
    try:
        if isinstance(path, str):
            path = Path(path)
        if path.exists():
            os.remove(path)
    except Exception as e:
        print(f"Không thể xóa {path}: {e}")

def get_video_id(url: str) -> str:
    """Lấy video_id từ link YouTube"""
    from urllib.parse import urlparse, parse_qs
    
    query = urlparse(url)

    if query.hostname == 'youtu.be':
        return query.path[1:]

    if query.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if query.path == '/watch':
            p_qs = parse_qs(query.query)
            if 'v' in p_qs:
                return p_qs['v'][0]
        if query.path.startswith('/embed/'):
            return query.path.split('/')[2]
        if query.path.startswith('/v/'):
            return query.path.split('/')[2]
        if query.path.startswith('/shorts/'):
            return query.path.split('/')[2]

    return None

import re
def clean_subtitle_text(text: str) -> str:
    """Xóa bỏ các ghi chú trong ngoặc vuông như [Music], [Applause]..."""
    if not text:
        return ""
    # Xóa nội dung trong ngoặc vuông []
    cleaned = re.sub(r'\[.*?\]', '', text)
    # Xóa khoảng trắng thừa
    return cleaned.strip()
