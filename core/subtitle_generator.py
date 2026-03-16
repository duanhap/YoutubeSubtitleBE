from .utils import format_timestamp

class SubtitleGenerator:
    @staticmethod
    def generate_srt_from_formatted(sections: list) -> str:
        """Tạo file SRT từ danh sách formatted_sections (output của API)
        
        Format mỗi section:
        {stt, starttime, endtime, content, pronunciation, translation}
        """
        srt_lines = []
        for sec in sections:
            srt_lines.append(str(sec["stt"]))
            srt_lines.append(f"{sec['starttime']} --> {sec['endtime']}")
            srt_lines.append(sec.get("content", ""))
            srt_lines.append(sec.get("pronunciation", ""))
            srt_lines.append(sec.get("translation", ""))
            srt_lines.append("")  # Dòng trống phân cách

        return "\n".join(srt_lines)

    @staticmethod
    def generate_srt_string(segments: list) -> str:
        """Tạo chuỗi SRT từ danh sách raw segments"""
        srt_lines = []
        for idx, seg in enumerate(segments, 1):
            start = format_timestamp(seg["start"])
            end_val = seg.get("end", seg["start"] + seg.get("duration", 2.0))
            end = format_timestamp(end_val)

            srt_lines.append(f"{idx}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(seg.get('kanji', seg.get('text', '')))
            srt_lines.append(seg.get('pronunciation', seg.get('hiragana', '')))
            srt_lines.append(seg.get('vietsub', ''))
            srt_lines.append("")

        return "\n".join(srt_lines)
