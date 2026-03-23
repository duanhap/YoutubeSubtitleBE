import sys
import os
import builtins

# Tạm thời ép utf-8 cho site-packages (epitran)
original_open = builtins.open
def utf8_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if 'b' not in mode and encoding is None:
        encoding = 'utf-8'
    return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

builtins.open = utf8_open

try:
    with open('result_ipa.txt', 'w', encoding='utf-8') as out:
        try:
            import epitran
            epi = epitran.Epitran('vie-Latn', tones=True)
            text = "Từng ngày ta luôn ao ước tìm một vùng"
            out.write(f"Input: {text}\n")
            res = epi.transliterate(text)
            out.write(f"IPA: {res}\n")
            print("Finished successfully")
        except Exception as e:
            out.write(f"Error: {e}\n")
            print("Finished with error")
finally:
    builtins.open = original_open
