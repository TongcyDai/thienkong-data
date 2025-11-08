#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《天光客語詞典》發音轉換工具
將原書拼音轉換為調號式客語拼音
"""

import json
import unicodedata
import re
import sys
from typing import Dict, List, Tuple


class HakkaPronunciationConverter:
    """客語發音轉換器"""
    
    # Unicode 附加符號對應
    DIACRITICS = {
        '\u0301': 'acute',        # ́  (combining acute accent)
        '\u0300': 'grave',        # ̀  (combining grave accent)
        '\u0304': 'macron',       # ̄  (combining macron)
        '\u0331': 'macron_below', # ̱  (combining macron below)
        '\u0323': 'dot_below',    # ̣  (combining dot below)
    }
    
    # 四縣聲調對應
    SIYEN_TONES = {
        'acute': '1',
        'grave': '2',
        'none': '3',           # 無符號，無入聲韻尾
        'dot_below': '4',      # 有入聲韻尾
        'macron_below': '5',
        'none_checked': '8',   # 無符號，有入聲韻尾
    }
    
    # 海陸聲調對應
    HOILIUK_TONES = {
        'grave': '1',
        'acute': '2',
        'macron_below': '3',
        'none_checked': '4',   # 無符號，有入聲韻尾
        'none': '5',           # 無符號，無入聲韻尾
        'macron': '7',
        'dot_below': '8',      # 有入聲韻尾
    }
    
    # 入聲韻尾（需要轉換）
    CHECKED_FINALS = {'p', 't', 'k'}
    CONVERTED_FINALS = {'p': 'b', 't': 'd', 'k': 'g'}
    
    # 聲母列表（按長度排序，確保先匹配長聲母如 zh, ch, sh, ng, rh, bb, gg, zz）
    INITIALS = ['zh', 'ch', 'sh', 'ng', 'rh', 'bb', 'gg', 'zz',
                'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 
                'p', 'q', 's', 't', 'v', 'x', 'z']
    
    # 四縣話特殊聲母轉換（當韻母以 i 開頭但不是 ii 開頭時）
    SIYEN_INITIAL_CONVERSION = {
        'z': 'j',
        'c': 'q',
        's': 'x'
    }
    
    # 四縣調型式聲調符號
    SIYEN_TONE_MARKS = {
        '1': 'ˊ',
        '2': 'ˋ',
        '3': '',    # 不標
        '4': 'ˋ',
        '5': 'ˇ',
        '8': '',    # 不標
    }
    
    # 海陸調型式聲調符號
    HOILIUK_TONE_MARKS = {
        '1': 'ˋ',
        '2': 'ˊ',
        '3': 'ˇ',
        '4': '',    # 不標
        '5': '',    # 不標
        '7': '+',
        '8': 'ˋ',
    }
    
    # 白話字聲母轉換（僅四縣）
    PFS_INITIAL_MAP = {
        'b': 'p',
        'p': 'ph',
        'd': 't',
        't': 'th',
        'g': 'k',
        'k': 'kh',
        'z': 'ch',
        'c': 'chh',
        'j': 'ch',
        'q': 'chh',
        'x': 's'
    }
    
    # 白話字韻尾轉換
    PFS_ENDING_MAP = {
        'b': 'p',
        'd': 't',
        'g': 'k'
    }
    
    # 白話字聲調符號（四縣）
    PFS_TONE_MARKS = {
        '1': '\u0302',  # ˆ circumflex
        '2': '\u0301',  # ´ acute
        '3': '',        # 不標記
        '4': '',        # 不標記
        '5': '\u0300',  # ` grave
        '8': '\u030D',  # ̍ vertical line above
    }
    
    def __init__(self, dialect: str):
        """
        初始化轉換器
        
        Args:
            dialect: 'siyen' (四縣) 或 'hoiliuk' (海陸)
        """
        if dialect not in ['siyen', 'hoiliuk']:
            raise ValueError("方言必須是 'siyen' 或 'hoiliuk'")
        
        self.dialect = dialect
        self.tone_map = self.SIYEN_TONES if dialect == 'siyen' else self.HOILIUK_TONES
    
    def _normalize_and_extract_tone(self, syllable: str) -> Tuple[str, str]:
        """
        將音節正規化並提取聲調信息
        
        Args:
            syllable: 原始音節
            
        Returns:
            (基底字母, 聲調類型)
        """
        # 使用 NFD 正規化，將附加符號分離
        normalized = unicodedata.normalize('NFD', syllable)
        
        # 提取附加符號（按優先級）
        base_chars = []
        tone_types = []
        
        for char in normalized:
            if char in self.DIACRITICS:
                tone_types.append(self.DIACRITICS[char])
            else:
                base_chars.append(char)
        
        base_syllable = ''.join(base_chars)
        
        # 當有多個附加符號時，按優先級選擇
        # 優先級：macron_below, dot_below > macron, acute, grave
        tone_type = None
        if tone_types:
            priority_order = ['macron_below', 'dot_below', 'macron', 'acute', 'grave']
            for priority_tone in priority_order:
                if priority_tone in tone_types:
                    tone_type = priority_tone
                    break
        
        return base_syllable, tone_type
    
    def _has_checked_final(self, syllable: str) -> bool:
        """
        檢查音節是否有入聲韻尾 (p, t, k)
        
        Args:
            syllable: 音節
            
        Returns:
            是否有入聲韻尾
        """
        return len(syllable) > 0 and syllable[-1] in self.CHECKED_FINALS
    
    def _split_syllable(self, syllable: str) -> Tuple[str, str]:
        """
        將音節拆分為聲母和韻母
        
        Args:
            syllable: 音節
            
        Returns:
            (聲母, 韻母) - 聲母可能為空字串
        """
        # 嘗試匹配聲母（從長到短）
        for initial in self.INITIALS:
            if syllable.startswith(initial):
                return initial, syllable[len(initial):]
        
        # 沒有聲母
        return '', syllable
    
    def _rhyme_starts_with_i_not_ii(self, rhyme: str) -> bool:
        """
        檢查韻母是否以單個 i 開頭（不是 ii）
        
        Args:
            rhyme: 韻母
            
        Returns:
            是否以單個 i 開頭
        """
        if not rhyme.startswith('i'):
            return False
        
        # 檢查是否是 ii 開頭
        if rhyme.startswith('ii'):
            return False
        
        return True
    
    def _convert_initial(self, initial: str, rhyme: str) -> str:
        """
        轉換聲母（僅四縣話需要）
        
        Args:
            initial: 聲母
            rhyme: 韻母
            
        Returns:
            轉換後的聲母
        """
        if self.dialect != 'siyen':
            return initial
        
        # 四縣話：z, c, s 在韻母以 i 開頭（但不是 ii）時轉換
        if initial in self.SIYEN_INITIAL_CONVERSION and self._rhyme_starts_with_i_not_ii(rhyme):
            return self.SIYEN_INITIAL_CONVERSION[initial]
        
        return initial
    
    def _convert_final(self, syllable: str) -> str:
        """
        轉換韻尾 p/t/k → b/d/g
        
        Args:
            syllable: 音節
            
        Returns:
            轉換後的音節
        """
        if self._has_checked_final(syllable):
            final = syllable[-1]
            return syllable[:-1] + self.CONVERTED_FINALS[final]
        return syllable
    
    def convert_syllable(self, original_syllable: str) -> str:
        """
        轉換單個音節
        
        Args:
            original_syllable: 原書拼音的音節
            
        Returns:
            調號式客語拼音的音節
        """
        if not original_syllable or original_syllable.isspace():
            return original_syllable
        
        # 提取基底音節和聲調類型
        base_syllable, tone_type = self._normalize_and_extract_tone(original_syllable)
        
        # 檢查是否有入聲韻尾
        has_checked = self._has_checked_final(base_syllable)
        
        # 拆分聲母和韻母
        initial, rhyme = self._split_syllable(base_syllable)
        
        # 轉換聲母（四縣話特殊處理）
        converted_initial = self._convert_initial(initial, rhyme)
        
        # 轉換韻尾 p/t/k → b/d/g
        converted_rhyme = self._convert_final(rhyme)
        
        # 判斷聲調
        if tone_type is None:
            # 無附加符號的情況
            if has_checked:
                if self.dialect == 'siyen':
                    tone = self.tone_map['none_checked']  # 第8調
                else:  # hoiliuk
                    tone = self.tone_map['none_checked']  # 第4調
            else:
                tone = self.tone_map['none']  # 四縣第3調 / 海陸第5調
        else:
            # 有附加符號的情況
            if tone_type == 'dot_below' and has_checked:
                tone = self.tone_map['dot_below']
            else:
                tone = self.tone_map.get(tone_type, '?')
        
        return converted_initial + converted_rhyme + tone
    
    def convert_pronunciation(self, original: str) -> str:
        """
        轉換完整的發音字符串
        
        Args:
            original: 原書拼音
            
        Returns:
            調號式客語拼音
        """
        if not original:
            return ""
        
        # 分割音節（以空格分隔）
        syllables = original.split()
        
        # 轉換每個音節
        converted_syllables = [self.convert_syllable(syl) for syl in syllables]
        
        return ' '.join(converted_syllables)
    
    def numbered_to_marked(self, numbered: str) -> str:
        """
        將調號式客語拼音轉換為調型式客語拼音
        
        Args:
            numbered: 調號式客語拼音
            
        Returns:
            調型式客語拼音
        """
        if not numbered:
            return ""
        
        # 選擇調型符號對應表
        tone_marks = self.SIYEN_TONE_MARKS if self.dialect == 'siyen' else self.HOILIUK_TONE_MARKS
        
        # 分割音節
        syllables = numbered.split()
        marked_syllables = []
        
        for syllable in syllables:
            # 提取調號（最後一個字符應該是數字）
            if not syllable:
                marked_syllables.append(syllable)
                continue
            
            if syllable[-1].isdigit():
                tone_number = syllable[-1]
                base = syllable[:-1]
                
                # 獲取調型符號
                tone_mark = tone_marks.get(tone_number, '')
                
                # 調型符號放在音節最後面
                marked = base + tone_mark
                
                marked_syllables.append(marked)
            else:
                # 沒有調號，保持原樣
                marked_syllables.append(syllable)
        
        return ' '.join(marked_syllables)
    
    def _convert_pfs_nucleus(self, nucleus: str) -> str:
        """
        轉換韻腹為白話字形式
        
        Args:
            nucleus: 韻腹
            
        Returns:
            白話字韻腹
        """
        if nucleus == 'ii':
            return 'ṳ'
        elif nucleus == 'ua':
            return 'oa'
        elif nucleus == 'ue':
            return 'oe'
        else:
            return nucleus
    
    def _handle_initial_i_pfs(self, nucleus: str) -> str:
        """
        處理沒有聲母時以 i 開頭的韻母（白話字規則）
        
        Args:
            nucleus: 韻母
            
        Returns:
            轉換後的韻母
        """
        if nucleus == 'i':
            return 'yi'
        elif nucleus.startswith('i'):
            return 'y' + nucleus[1:]
        else:
            return nucleus
    
    def _find_pfs_tone_target(self, nucleus: str) -> tuple:
        """
        找到白話字中應該標記聲調的元音位置
        元音優先級：a > o > e > u > ṳ > i
        
        Args:
            nucleus: 韻母（已轉換為白話字形式）
            
        Returns:
            (index, char) 元組
        """
        # 特殊情況：oa 開頭時標在 o 上
        if nucleus.startswith('oa'):
            return (0, 'o')
        
        # 元音優先級順序
        vowel_priority = ['a', 'o', 'e', 'u', 'ṳ', 'i']
        
        for vowel in vowel_priority:
            index = nucleus.find(vowel)
            if index != -1:
                return (index, vowel)
        
        # 鼻音韻尾作為音節核心
        if nucleus == 'm':
            return (0, 'm')
        elif nucleus == 'n':
            return (0, 'n')
        elif nucleus == 'ng':
            return (0, 'n')  # ng 時標在 n 上
        
        return (-1, '')
    
    def _apply_pfs_tone_mark(self, syllable: str, tone_target: tuple, tone_number: str) -> str:
        """
        在白話字音節上標記聲調
        
        Args:
            syllable: 音節
            tone_target: (位置, 字符) 元組
            tone_number: 調號
            
        Returns:
            標記後的音節
        """
        if tone_target[0] == -1:
            return syllable
        
        tone_mark = self.PFS_TONE_MARKS.get(tone_number, '')
        if not tone_mark:
            return syllable  # 3調和4調不標記
        
        index = tone_target[0]
        char = tone_target[1]
        
        # 在指定位置插入聲調符號
        return syllable[:index] + char + tone_mark + syllable[index + 1:]
    
    def numbered_to_pfs(self, numbered: str) -> str:
        """
        將調號式客語拼音轉換為白話字（僅四縣）
        
        Args:
            numbered: 調號式客語拼音
            
        Returns:
            白話字（Pha̍k-fa-sṳ）
        """
        if not numbered:
            return ""
        
        if self.dialect != 'siyen':
            # 海陸腔暫時不支援白話字轉換
            return ""
        
        # 分割音節
        syllables = numbered.split()
        pfs_syllables = []
        
        for syllable in syllables:
            if not syllable:
                continue
            
            # 提取調號（最後一個字符應該是數字）
            if syllable[-1].isdigit():
                tone_number = syllable[-1]
                base = syllable[:-1]
            else:
                # 沒有調號，視為第3調
                tone_number = '3'
                base = syllable
            
            # 特殊處理：只有鼻音韻尾的情況（m, n, ng）
            if base in ['m', 'n', 'ng']:
                pfs_base = base
                # 找到標記位置
                if base == 'ng':
                    tone_target = (0, 'n')  # ng 標在 n 上
                else:
                    tone_target = (0, base[0])
                
                # 標記聲調
                pfs_syllable = self._apply_pfs_tone_mark(pfs_base, tone_target, tone_number)
                pfs_syllables.append(pfs_syllable)
                continue
            
            # 拆分聲母和韻母
            initial, rhyme = self._split_syllable(base)
            
            # 轉換聲母
            pfs_initial = self.PFS_INITIAL_MAP.get(initial, initial) if initial else ''
            
            # 檢查韻尾
            has_ending = len(rhyme) > 0 and rhyme[-1] in ['b', 'd', 'g', 'm', 'n']
            # 特殊處理 ng 韻尾
            if len(rhyme) >= 2 and rhyme[-2:] == 'ng':
                ending = 'ng'
                nucleus = rhyme[:-2]
            elif has_ending:
                ending = rhyme[-1]
                nucleus = rhyme[:-1]
            else:
                ending = ''
                nucleus = rhyme
            
            # 轉換韻腹
            pfs_nucleus = self._convert_pfs_nucleus(nucleus)
            
            # 如果沒有聲母且韻母以 i 開頭，特殊處理
            if not initial and pfs_nucleus.startswith('i'):
                pfs_nucleus = self._handle_initial_i_pfs(pfs_nucleus)
            
            # 轉換韻尾
            pfs_ending = self.PFS_ENDING_MAP.get(ending, ending) if ending else ''
            
            # 組合音節
            pfs_base = pfs_initial + pfs_nucleus + pfs_ending
            
            # 找到標記聲調的位置
            tone_target = self._find_pfs_tone_target(pfs_nucleus)
            
            # 調整位置（加上聲母長度）
            adjusted_target = (tone_target[0] + len(pfs_initial), tone_target[1])
            
            # 標記聲調
            pfs_syllable = self._apply_pfs_tone_mark(pfs_base, adjusted_target, tone_number)
            
            pfs_syllables.append(pfs_syllable)
        
        # 用連字號連接音節，並使用 NFC 正規化
        result = '-'.join(pfs_syllables) if pfs_syllables else ""
        return unicodedata.normalize('NFC', result)


def process_json_file(input_file: str, output_file: str, dialect: str):
    """
    處理 JSON 檔案，添加調號式、調型式和白話字客語拼音
    
    Args:
        input_file: 輸入 JSON 檔案路徑
        output_file: 輸出 JSON 檔案路徑
        dialect: 方言類型 ('siyen' 或 'hoiliuk')
    """
    print(f"讀取檔案: {input_file}")
    
    # 讀取 JSON 檔案
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 檢查 JSON 格式：是數組還是包含 entries 的對象
    if isinstance(data, dict) and 'entries' in data:
        # 格式：{"total": ..., "entries": [...]}
        entries = data['entries']
        is_wrapped = True
    elif isinstance(data, list):
        # 格式：[...]
        entries = data
        is_wrapped = False
    else:
        print("錯誤：無法識別的 JSON 格式")
        return
    
    # 初始化轉換器
    converter = HakkaPronunciationConverter(dialect)
    
    # 處理每個 entry
    processed_count = 0
    for entry in entries:
        if 'pronunciation' in entry and 'original' in entry['pronunciation']:
            original = entry['pronunciation']['original']
            
            # 轉換為調號式客語拼音
            numbered = converter.convert_pronunciation(original)
            entry['pronunciation']['numbered'] = numbered
            
            # 轉換為調型式客語拼音
            marked = converter.numbered_to_marked(numbered)
            entry['pronunciation']['marked'] = marked
            
            # 轉換為白話字（僅四縣）
            if dialect == 'siyen':
                pfs = converter.numbered_to_pfs(numbered)
                if pfs:  # 只有成功轉換時才添加
                    entry['pronunciation']['pfs'] = pfs
            
            processed_count += 1
            
            # 顯示進度（每100個）
            if processed_count % 100 == 0:
                print(f"已處理 {processed_count} 個條目...")
    
    # 如果是包裝格式，更新 entries；否則直接使用 entries
    if is_wrapped:
        data['entries'] = entries
        output_data = data
    else:
        output_data = entries
    
    # 寫入輸出檔案
    print(f"寫入檔案: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"完成！共處理 {processed_count} 個條目")
    print(f"方言: {'四縣' if dialect == 'siyen' else '海陸'}")


def main():
    """主程式"""
    print("=" * 60)
    print("《天光客語詞典》發音轉換工具")
    print("=" * 60)
    
    # 獲取方言類型
    if len(sys.argv) > 1:
        dialect = sys.argv[1].lower()
    else:
        print("\n請選擇方言類型：")
        print("  siyen   - 四縣腔")
        print("  hoiliuk - 海陸腔")
        dialect = input("\n請輸入方言代碼: ").strip().lower()
    
    if dialect not in ['siyen', 'hoiliuk']:
        print("錯誤：方言必須是 'siyen' 或 'hoiliuk'")
        sys.exit(1)
    
    # 獲取檔案路徑
    if len(sys.argv) > 3:
        input_file = sys.argv[2]
        output_file = sys.argv[3]
    else:
        input_file = input("\n輸入 JSON 檔案路徑: ").strip()
        output_file = input("輸出 JSON 檔案路徑: ").strip()
    
    # 處理檔案
    try:
        process_json_file(input_file, output_file, dialect)
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {input_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"錯誤：{input_file} 不是有效的 JSON 檔案")
        sys.exit(1)
    except Exception as e:
        print(f"錯誤：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()