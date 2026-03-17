from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from faster_whisper import WhisperModel

from core.config import UPLOAD_DIR, MODEL_CONFIG
from core.youtube_service import YouTubeService
from core.translation_service import translation_service
from core.subtitle_generator import SubtitleGenerator
from core.utils import get_video_id, safe_remove, format_timestamp, clean_subtitle_text

# Load env từ thư mục cha
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="MIRA BE V2 - Job System")

# Lưu trữ trạng thái công việc (Cache trong RAM)
jobs: Dict[str, Dict[str, Any]] = {}

import json
def save_job_to_file(job_id: str, data: dict):
    """Lưu kết quả job vào file JSON"""
    file_path = UPLOAD_DIR / f"{job_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_job_from_file(job_id: str) -> Optional[dict]:
    """Đọc kết quả job từ file JSON"""
    file_path = UPLOAD_DIR / f"{job_id}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# Khởi tạo YT Service
yt_service = YouTubeService(
    translation_service,
    proxy_username=os.getenv("PROXY_USERNAME"),
    proxy_password=os.getenv("PROXY_PASSWORD"),
    proxy_ip=os.getenv("PROXY_IP")
)

# Khởi tạo Faster Whisper
model = WhisperModel(
    MODEL_CONFIG["model_size"],
    device=MODEL_CONFIG["device"],
    compute_type=MODEL_CONFIG["compute_type"]
)

class YouTubeRequest(BaseModel):
    sourceurl: str
    termlanguagecode: str = "ja"
    definitionlanguagecode: str = "vi"

def background_worker(job_id: str, req: YouTubeRequest):
    """Hàm chạy ngầm xử lý video"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 5
        
        video_id = get_video_id(req.sourceurl)
        if not video_id:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = "Invalid YouTube URL"
            return

        segments_data: List[Dict[str, Any]] = []
        source = "youtube_subs"

        # 1. Thử lấy sub trực tiếp từ YouTube
        source_subs, target_subs = yt_service.get_youtube_subtitles(video_id, lang_code=req.termlanguagecode, target_lang=req.definitionlanguagecode)
        
        def update_progress(p):
            if jobs.get(job_id, {}).get("status") == "cancelled":
                raise Exception("Job cancelled by user")
            # Tiến trình dịch chiếm từ 20% đến 90%
            jobs[job_id]["progress"] = 20 + int(p * 0.7)

        if (source_subs and len(source_subs) > 0) or (target_subs and len(target_subs) > 0):
            jobs[job_id]["progress"] = 15
            segments_data = yt_service.process_youtube_subtitles(
                source_subs, target_subs, 
                lang_code=req.termlanguagecode,
                target_lang=req.definitionlanguagecode,
                progress_callback=update_progress
            )
        
        # 2. Thu fetch direct nếu bước 1 fail
        if not segments_data:
            jobs[job_id]["progress"] = 15
            direct_subs = yt_service.fetch_direct_subtitles(video_id, languages=[req.termlanguagecode, req.definitionlanguagecode])
            if direct_subs:
                source = "youtube_direct"
                total = len(direct_subs)
                for i, s in enumerate(direct_subs):
                    if jobs.get(job_id, {}).get("status") == "cancelled":
                        raise Exception("Job cancelled by user")
                    
                    text = clean_subtitle_text(s['text'])
                    if not text: continue
                    vietsub = translation_service.translate(text, source=req.termlanguagecode, target=req.definitionlanguagecode)
                    vietsub = clean_subtitle_text(vietsub)
                    if not vietsub: continue
                    
                    segments_data.append({
                        "start": s['start'],
                        "end": s['start'] + s.get('duration', 2.0),
                        "kanji": text,
                        "pronunciation": translation_service.get_pronunciation(text, lang_code=req.termlanguagecode),
                        "vietsub": vietsub
                    })
                    jobs[job_id]["progress"] = 20 + int(((i+1)/total) * 70)

        # 3. Whisper Fallback
        if not segments_data:
            source = "whisper"
            jobs[job_id]["progress"] = 20
            audio_path = UPLOAD_DIR / f"{job_id}.m4a"
            if yt_service.download_youtube_audio(req.sourceurl, audio_path):
                jobs[job_id]["progress"] = 50
                try:
                    whisper_segments, _ = model.transcribe(str(audio_path), language=req.termlanguagecode)
                    # Whisper trả về generator, ta chuyển sang list để tính toán
                    seg_list = list(whisper_segments)
                    total = len(seg_list)
                    for i, w_seg in enumerate(seg_list):
                        if jobs.get(job_id, {}).get("status") == "cancelled":
                            raise Exception("Job cancelled by user")
                            
                        text = clean_subtitle_text(w_seg.text)
                        if not text: continue
                        vietsub = translation_service.translate(text, source=req.termlanguagecode, target=req.definitionlanguagecode)
                        vietsub = clean_subtitle_text(vietsub)
                        if not vietsub: continue

                        segments_data.append({
                            "start": w_seg.start,
                            "end": w_seg.end,
                            "kanji": text,
                            "pronunciation": translation_service.get_pronunciation(text, lang_code=req.termlanguagecode),
                            "vietsub": vietsub
                        })
                        jobs[job_id]["progress"] = 50 + int(((i+1)/total) * 45)
                finally:
                    safe_remove(audio_path)

        if not segments_data:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = "No subtitles could be generated"
            return

        # 4. Format kết quả cuối cùng
        formatted_sections = []
        for idx, seg in enumerate(segments_data, 1):
            start_val = float(seg.get("start", 0.0))
            end_val = float(seg.get("end", start_val + 2.0))
            formatted_sections.append({
                "stt": idx,
                "starttime": format_timestamp(start_val),
                "endtime": format_timestamp(end_val),
                "content": seg.get("kanji", ""),
                "pronunciation": seg.get("pronunciation", ""),
                "translation": seg.get("vietsub", "")
            })

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = formatted_sections
        jobs[job_id]["source"] = source
        
        # Lưu JSON để bền vững (Persistent)
        save_job_to_file(job_id, jobs[job_id])
        
        # Tạo file SRT
        from core.subtitle_generator import SubtitleGenerator
        srt_content = SubtitleGenerator.generate_srt_from_formatted(formatted_sections)
        srt_path = UPLOAD_DIR / f"{job_id}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        print(f"✅ Đã lưu file SRT: {srt_path}")
        
        # Tải video mp4 về server
        video_path = UPLOAD_DIR / f"{job_id}.mp4"
        video_downloaded = yt_service.download_youtube_video(req.sourceurl, video_path)
        if video_downloaded:
            jobs[job_id]["video_url"] = f"/video/{job_id}"
        else:
            jobs[job_id]["video_url"] = None
            print(f"⚠️ Không tải được video, bỏ qua.")
        
        # Cập nhật lại JSON với video_url
        save_job_to_file(job_id, jobs[job_id])

    except Exception as e:
        import traceback
        print(f"❌ Job Error: {traceback.format_exc()}")
        
        # Nếu đã bị hủy thì không ghi đè thành failed
        if jobs.get(job_id, {}).get("status") == "cancelled":
            save_job_to_file(job_id, jobs[job_id])
            return
            
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = str(e)
        save_job_to_file(job_id, jobs[job_id])

@app.post("/youtube")
async def process_youtube(req: YouTubeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "result": None,
        "message": None
    }
    background_tasks.add_task(background_worker, job_id, req)
    return {
        "success": True,
        "message": "Job started",
        "data": {
            "job_id": job_id,
            "video_url": req.sourceurl
        }
    }

@app.get("/progress/{job_id}")
async def get_progress(job_id: str):
    # 1. Kiểm tra trong RAM trước
    if job_id in jobs:
        job = jobs[job_id]
    else:
        # 2. Nếu không có trong RAM (do restart), thử tìm trong file
        job = load_job_from_file(job_id)
        if job:
            # Khôi phục vào RAM để lần sau lấy nhanh hơn
            jobs[job_id] = job
        else:
            return {"success": False, "message": "Job not found"}
    
    return {
        "success": True,
        "status": job["status"],
        "progress": job.get("progress", 0),
        "message": job.get("message"),
        "video_url": job.get("video_url"),
        "data": job.get("result") if job["status"] == "completed" else []
    }

@app.get("/download/{job_id}")
async def download_srt(job_id: str):
    srt_path = UPLOAD_DIR / f"{job_id}.srt"
    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="SRT file not found")
    
    return FileResponse(
        path=srt_path,
        filename=f"{job_id}.srt",
        media_type='application/x-subrip'
    )

@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    # Tìm trong cả RAM và File
    if job_id not in jobs:
        job = load_job_from_file(job_id)
        if job:
            jobs[job_id] = job
        else:
            return {"success": False, "message": "Job not found"}
            
    status = jobs[job_id]["status"]
    if status in ["completed", "failed", "cancelled"]:
        return {"success": False, "message": f"Job is already {status}"}
        
    jobs[job_id]["status"] = "cancelled"
    jobs[job_id]["message"] = "Job cancelled by user"
    
    return {"success": True, "message": "Job cancellation requested"}

@app.get("/video/{job_id}")
async def stream_video(job_id: str):
    """Serve file video mp4 để ExoPlayer stream"""
    video_path = UPLOAD_DIR / f"{job_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found or not yet downloaded")
    
    return FileResponse(
        path=video_path,
        filename=f"{job_id}.mp4",
        media_type="video/mp4"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
