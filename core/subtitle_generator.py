from .utils import format_timestamp

class SubtitleGenerator:
    @staticmethod
    def generate_srt_string(segments: list) -> str:
        """Tạo chuỗi SRT từ danh sách segments"""
        srt_lines = []
        for idx, seg in enumerate(segments, 1):
            start = format_timestamp(seg["start"])
            # 'end' might be calculated if not present
            end_val = seg.get("end", seg["start"] + seg.get("duration", 2.0))
            end = format_timestamp(end_val)
            
            srt_lines.append(f"{idx}")
            srt_lines.append(f"{start} --> {end}")
            
            # BE_Simple style: term, reading, definition
            srt_lines.append(f"{seg.get('kanji', seg.get('text', ''))}")  
            srt_lines.append(f"{seg.get('hiragana', '')}")
            srt_lines.append(f"{seg.get('vietsub', '')}")
            srt_lines.append("") 
            
        return "\n".join(srt_lines)

    @staticmethod
    def create_segment_data(text, start, end, source_lang, target_lang, translation_service) -> dict:
        """Helper to format data similar to BE_Simple but using improved service"""
        kanji = text.strip()
        hira = ""
        if source_lang == 'ja':
            hira = translation_service.to_hiragana(kanji)
        
        vietsub = translation_service.translate(kanji, source=source_lang, target=target_lang)
        
        return {
            "start": start,
            "end": end,
            "kanji": kanji,
            "hiragana": hira,
            "vietsub": vietsub
        }
