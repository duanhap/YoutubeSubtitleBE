import subprocess
import os
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from .utils import get_video_id, safe_remove, clean_subtitle_text
from typing import Optional, Tuple, List, Dict, Any, Union

class YouTubeService:
    def __init__(self, translation_service, proxy_username: Optional[str] = None, proxy_password: Optional[str] = None, proxy_ip: Optional[str] = None):
        self.translation_service = translation_service
        self.proxy_config = None
        self.proxy_url: Optional[str] = None
        
        # Cấu hình proxy nếu có thông tin (Giống BE lớn)
        if proxy_username and proxy_password:
            self.proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
                filter_ip_locations=["us", "jp", "vn"]
            )
            # Proxy URL cho yt-dlp
            host = proxy_ip if proxy_ip else "p.webshare.io:80"
            self.proxy_url = f"http://{proxy_username}:{proxy_password}@{host}"
            print(f"🔧 YouTubeService initialized with proxy: {host}")
        else:
            print("⚠️ YouTubeService initialized WITHOUT proxy credentials")

    def get_youtube_subtitles(self, video_id: str, lang_code: str = 'ja', target_lang: str = 'vi') -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """Lấy phụ đề từ YouTube với cơ chế Fallback: Proxy -> No Proxy"""
        
        # Chiến lược 1: Thử có Proxy (nếu có config)
        if self.proxy_config:
            try:
                print(f"🌐 Đang thử lấy transcript với PROXY cho video {video_id}...")
                yt_api = YouTubeTranscriptApi(proxy_config=self.proxy_config)
                return self._fetch_from_api(yt_api, video_id, lang_code, target_lang)
            except Exception as e:
                print(f"⚠️ Thử với Proxy thất bại (có thể dính 429): {e}")
        
        # Chiến lược 2: Thử KHÔNG Proxy (hoặc fallback nếu proxy lỗi)
        try:
            print(f"🏠 Đang thử lấy transcript TRỰC TIẾP (No Proxy) cho video {video_id}...")
            yt_api = YouTubeTranscriptApi()
            return self._fetch_from_api(yt_api, video_id, lang_code, target_lang)
        except Exception as e:
            print(f"❌ Lỗi khi lấy transcripts (cả proxy và trực tiếp đều thất bại): {e}")
            return None, None

    def _fetch_from_api(self, yt_api: YouTubeTranscriptApi, video_id: str, lang_code: str, target_lang: str) -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """Helper để gọi API tìm sub theo ngôn ngữ yêu cầu"""
        transcript_list = yt_api.list(video_id)
        
        source_subs, target_subs = None, None
        
        # Tìm ngôn ngữ gốc (ví dụ: Nhật/Anh)
        try:
            source_transcript = transcript_list.find_manually_created_transcript([lang_code])
            source_subs = [{'text': seg.text, 'start': seg.start, 'duration': seg.duration} for seg in source_transcript.fetch()]
            print(f"✅ Đã tìm thấy {len(source_subs)} dòng {lang_code} (Manual)")
        except:
            try:
                source_transcript = transcript_list.find_generated_transcript([lang_code])
                source_subs = [{'text': seg.text, 'start': seg.start, 'duration': seg.duration} for seg in source_transcript.fetch()]
                print(f"✅ Đã tìm thấy {len(source_subs)} dòng {lang_code} (Auto)")
            except: pass
        
        # Tìm ngôn ngữ đích (ví dụ: Việt)
        try:
            target_transcript = transcript_list.find_manually_created_transcript([target_lang])
            target_subs = [{'text': seg.text, 'start': seg.start, 'duration': seg.duration} for seg in target_transcript.fetch()]
            print(f"✅ Đã tìm thấy {len(target_subs)} dòng {target_lang} (Manual)")
        except:
            try:
                target_transcript = transcript_list.find_generated_transcript([target_lang])
                target_subs = [{'text': seg.text, 'start': seg.start, 'duration': seg.duration} for seg in target_transcript.fetch()]
                print(f"✅ Đã tìm thấy {len(target_subs)} dòng {target_lang} (Auto)")
            except: pass
        
        return source_subs, target_subs

    def fetch_direct_subtitles(self, video_id: str, languages: List[str] = ['ja', 'vi', 'en']) -> Optional[List[Dict]]:
        """Lấy phụ đề trực tiếp"""
        try:
            if self.proxy_config:
                yt_api = YouTubeTranscriptApi(proxy_config=self.proxy_config)
            else:
                yt_api = YouTubeTranscriptApi()
                
            transcript = yt_api.fetch(video_id, languages=languages)
            return [{'text': seg.text, 'start': seg.start, 'duration': seg.duration} for seg in transcript]
        except Exception as e:
            print(f"❌ Lỗi khi lấy phụ đề trực tiếp: {e}")
            return None

    def download_youtube_audio(self, url: str, output_path: Path) -> bool:
        """Tải audio từ YouTube using yt-dlp (Bản cập nhật từ BE lớn)"""
        try:
            print(f"🎵 Đang tải audio từ YouTube: {url}")
            command = [
                "yt-dlp",
                "-f", "bestaudio/best",
                "-x", "--audio-format", "m4a",
                "-o", str(output_path),
                "--no-warnings",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            
            # Dùng proxy nếu dính 403 hoặc server bị chặn
            if self.proxy_url:
                print(f"📡 Sử dụng PROXY để tải audio...")
                command.extend(["--proxy", str(self.proxy_url)])

            command.append(url)
            
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if output_path.exists():
                print(f"✅ Tải audio thành công: {output_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Lỗi tải audio/yt-dlp: {e}")
            return False

    def download_youtube_video(self, url: str, output_path: Path) -> bool:
        """Tải video mp4 từ YouTube dùng yt-dlp"""
        try:
            print(f"🎬 Đang tải video từ YouTube: {url}")
            command = [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/mp4",
                "--merge-output-format", "mp4",
                "-o", str(output_path),
                "--no-warnings",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]

            if self.proxy_url:
                command.extend(["--proxy", str(self.proxy_url)])

            command.append(url)

            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if output_path.exists():
                print(f"✅ Tải video thành công: {output_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Lỗi tải video/yt-dlp: {e}")
            return False

    def process_youtube_subtitles(self, source_subs: Optional[List[Dict]], target_subs: Optional[List[Dict]], lang_code: str = 'ja', target_lang: str = 'vi', progress_callback=None) -> List[Dict[str, Any]]:
        """Xử lý phụ đề: Hỗ trợ linh hoạt ngôn ngữ gốc và đích"""
        result = []
        
        # 1. TRƯỜNG HỢP CÓ CẢ 2: Merge
        if source_subs and target_subs:
            len_src = len(source_subs)
            len_tgt = len(target_subs)
            diff_ratio = abs(len_src - len_tgt) / max(len_src, len_tgt)
            
            if diff_ratio < 0.2:
                print(f"🔗 Đang merge {len_src} dòng {lang_code} và {len_tgt} dòng {target_lang}...")
                min_len = min(len_src, len_tgt)
                for i in range(min_len):
                    src_sub = source_subs[i]
                    tgt_sub = target_subs[i]
                    text = clean_subtitle_text(src_sub['text'])
                    if not text: continue
                    result.append({
                        "start": src_sub['start'],
                        "end": src_sub['start'] + src_sub['duration'],
                        "kanji": text,
                        "pronunciation": self.translation_service.get_pronunciation(text, lang_code=lang_code),
                        "vietsub": clean_subtitle_text(tgt_sub['text'])
                    })
                return result
            else:
                print(f"⚠️ Độ dài {lang_code} ({len_src}) và {target_lang} ({len_tgt}) quá khác biệt. Ưu tiên dùng nguồn rồi dịch.")

        # 2. TRƯỜNG HỢP ƯU TIÊN: Dùng nguồn và dịch song song
        if source_subs and len(source_subs) > 0:
            print(f"🈯 Đang xử lý {len(source_subs)} dòng {lang_code} và dịch song sống sang {target_lang}...")
            
            # Làm sạch DANH SÁCH trước khi gửi đi dịch để đồng bộ index
            cleaned_src_texts = [clean_subtitle_text(sub['text']) for sub in source_subs]
            
            translated_list = self.translation_service.translate_batch(
                cleaned_src_texts, 
                source=lang_code, 
                target=target_lang,
                progress_callback=progress_callback
            )
            
            for i, sub in enumerate(source_subs):
                text = cleaned_src_texts[i]
                if not text: continue # Bỏ qua đoạn rác âm thanh ở nguồn
                
                # Làm sạch kết quả dịch một lần nữa
                vietsub = clean_subtitle_text(translated_list[i])
                if not vietsub: continue # Bỏ qua nếu bản dịch là rác
                
                result.append({
                    "start": sub['start'],
                    "end": sub['start'] + sub['duration'],
                    "kanji": text,
                    "pronunciation": self.translation_service.get_pronunciation(text, lang_code=lang_code),
                    "vietsub": vietsub
                })
            return result
        
        # 3. TRƯỜNG HỢP CUỐI: Chỉ có target
        if target_subs and len(target_subs) > 0:
            print(f"🇻🇳 Đang xử lý {len(target_subs)} dòng {target_lang} gốc...")
            for sub in target_subs:
                text = clean_subtitle_text(sub['text'])
                if not text: continue
                result.append({
                    "start": sub['start'],
                    "end": sub['start'] + sub['duration'],
                    "kanji": "",
                    "pronunciation": "",
                    "vietsub": text
                })
            return result
        
        print("⚠️ Không có dòng phụ đề nào để xử lý.")
        return result
