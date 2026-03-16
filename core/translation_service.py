import pykakasi
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style
import eng_to_ipa as ipa
from concurrent.futures import ThreadPoolExecutor
from typing import List

class TranslationService:
    def __init__(self):
        self.kks = pykakasi.kakasi()
        self.translators = {} # cache translators for different lang pairs
    
    def to_hiragana(self, text: str) -> str:
        """Chuyển text sang Hiragana (Tiếng Nhật)"""
        result = self.kks.convert(text)
        return "".join([item['hira'] for item in result])
    
    def get_pronunciation(self, text: str, lang_code: str = 'ja') -> str:
        """Lấy phiên âm chuyên nghiệp cho 4 ngôn ngữ chính"""
        if not text:
            return ""
        
        lang = lang_code.lower()
        
        # 1. Tiếng Anh -> IPA
        if lang == 'en':
            return ipa.convert(text)
            
        # 2. Tiếng Nhật -> Hiragana (Chuẩn sư phạm Nhật)
        elif lang == 'ja':
            return self.to_hiragana(text)
            
        # 3. Tiếng Trung -> Pinyin có dấu (Hệ thống phiên âm chuẩn nhất cho người học)
        elif lang == 'zh' or lang == 'zh-cn':
            py_list = pinyin(text, style=Style.TONE)
            return " ".join([item[0] for item in py_list])
            
        # 4. Tiếng Việt -> Giữ nguyên (Vì tiếng Việt đã là chữ tượng thanh/phonetic)
        elif lang == 'vi':
            return text
            
        return ""
    
    def _map_lang_code(self, lang: str) -> str:
        """Map common lang codes to deep-translator supported codes"""
        lang = lang.lower()
        if lang == 'zh':
            return 'zh-CN' # Default to Simplified Chinese
        return lang

    def translate(self, text: str, source: str = 'ja', target: str = 'vi') -> str:
        """Dịch văn bản đơn lẻ"""
        if not text.strip():
            return text
            
        source = self._map_lang_code(source)
        target = self._map_lang_code(target)
        
        if source == target:
            return text
            
        key = f"{source}_{target}"
        if key not in self.translators:
            self.translators[key] = GoogleTranslator(source=source, target=target)
        try:
            return self.translators[key].translate(text)
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def translate_batch(self, texts: List[str], source: str = 'ja', target: str = 'vi', progress_callback=None) -> List[str]:
        """Dịch danh sách văn bản song song và báo cáo tiến trình"""
        if source == target or not texts:
            return texts
            
        results = [None] * len(texts)
        total = len(texts)
        
        # Sử dụng 10 luồng
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Tạo list các task
            future_to_index = {executor.submit(self.translate, text, source, target): i for i, text in enumerate(texts)}
            
            from concurrent.futures import as_completed
            done_count = 0
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                results[index] = future.result()
                done_count += 1
                # Gọi callback báo cáo %
                if progress_callback:
                    progress_callback(int((done_count / total) * 100))
                    
        return results

# Global instance
translation_service = TranslationService()
