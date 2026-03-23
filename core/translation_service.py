import pykakasi
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style
import eng_to_ipa as ipa
import os
import builtins
import unicodedata
import re
import traceback
import csv
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

# Từ điển ánh xạ từ vựng tiếng Việt (Khởi tạo trì hoãn)
VI_IPA_MAP = None
VI_REPLACEMENT_PATTERN = None

class TranslationService:
    def __init__(self):
        self.kks = pykakasi.kakasi()
        self._vn_initialized = False

    def _init_vn_ipa(self):
        """Khởi tạo từ điển phiên âm Tiếng Việt thuần Python (Cực kỳ ổn định)"""
        global VI_IPA_MAP, VI_REPLACEMENT_PATTERN
        if self._vn_initialized:
            return
            
        print("🔧 Loading Vietnamese IPA Syllable Map...")
        try:
            # Đường dẫn file CSV từ Epitran đã cài đặt
            import site
            site_paths = site.getsitepackages()
            csv_path = None
            for p in site_paths:
                potential = os.path.join(p, 'epitran', 'data', 'map', 'vie-Latn.csv')
                if os.path.exists(potential):
                    csv_path = potential
                    break
            
            if not csv_path:
                print("⚠️ vie-Latn.csv not found, using basic fallback.")
                VI_IPA_MAP = {}
            else:
                # Đọc CSV với mã hóa UTF-8 (TỰ KIỂM SOÁT)
                temp_map = {}
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader) # Bỏ header Orth,Phon
                    for row in reader:
                        if len(row) >= 2:
                            orth, phon = row[0], row[1]
                            # Xử lý các token đặc biệt như <GI>
                            phon = phon.replace("<GI>", "z")
                            if orth:
                                temp_map[orth] = phon
                
                # Sắp xếp theo độ dài giảm dần để match dài nhất trước
                VI_IPA_MAP = dict(sorted(temp_map.items(), key=lambda x: len(x[0]), reverse=True))
                
                # Tạo Regex pattern cực nhanh
                # Escaping keys for regex
                keys = [re.escape(k) for k in VI_IPA_MAP.keys()]
                pattern_str = "|".join(keys)
                VI_REPLACEMENT_PATTERN = re.compile(pattern_str)
                
                print(f"✅ Loaded {len(VI_IPA_MAP)} Vietnamese mappings.")
        except Exception as e:
            print(f"❌ Failed to load Vietnamese map: {e}")
            traceback.print_exc()
            VI_IPA_MAP = {}
        
        self._vn_initialized = True

    def _pure_vi_transliterate(self, text: str) -> str:
        """Thực hiện phiên âm dùng Regex cực nhanh và ổn định"""
        if not VI_IPA_MAP or not VI_REPLACEMENT_PATTERN:
            return text
            
        # Chuẩn hóa Unicode
        text = unicodedata.normalize('NFC', text).lower()
        
        # Regex callback replacement
        def replace_func(match):
            return VI_IPA_MAP.get(match.group(0), match.group(0))
            
        return VI_REPLACEMENT_PATTERN.sub(replace_func, text)
    
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
            
        # 4. Tiếng Việt -> IPA (Sử dụng giải pháp Pure Python cực kỳ ổn định)
        elif lang == 'vi':
            self._init_vn_ipa()
            return self._pure_vi_transliterate(text)
            
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
            
        try:
            translator = GoogleTranslator(source=source, target=target)
            return translator.translate(text)
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def translate_batch(self, texts: List[str], source: str = 'ja', target: str = 'vi', progress_callback=None) -> List[str]:
        """Dịch danh sách văn bản song song và báo cáo tiến trình"""
        if source == target or not texts:
            return texts
            
        results: List[str] = [""] * len(texts)
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
