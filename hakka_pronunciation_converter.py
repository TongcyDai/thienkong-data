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

    # IPA 聲母轉換表（四縣、海陸共用）
    IPA_INITIAL_MAP = {
        'b': 'p', 'p': 'pʰ', 'm': 'm', 'f': 'f', 'v': 'v', 'bb': 'b',
        'd': 't', 't': 'tʰ', 'n': 'n', 'l': 'l',
        'g': 'k', 'k': 'kʰ', 'ng': 'ŋ', 'h': 'h', 'gg': 'g',
        'z': 't͡s', 'c': 't͡sʰ', 's': 's', 'zz': 'z',
        'j': 't͡ɕ', 'q': 't͡ɕʰ', 'x': 'ɕ',
        'zh': 't͡ʃ', 'ch': 't͡ʃʰ', 'sh': 'ʃ', 'rh': 'ʒ',
    }

    # 四縣話聲調調值
    SIYEN_TONE_VALUES = {
        '1': '²⁴', '2': '³¹', '3': '⁵⁵', '4': '²', '5': '¹¹', '8': '⁵'
    }

    # 海陸話聲調調值
    HOILIUK_TONE_VALUES = {
        '1': '⁵³', '2': '²⁴', '3': '¹¹', '4': '⁵', '5': '⁵⁵', '7': '³³', '8': '²'
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
        轉換韻尾 p/t/k → b/d/g, ⁿ → nn

        Args:
            syllable: 音節

        Returns:
            轉換後的音節
        """
        # 先處理鼻化韻尾 ⁿ → nn
        syllable = syllable.replace('ⁿ', 'nn')

        # 再處理入聲韻尾 p/t/k → b/d/g
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
    
    def _separate_syllable_and_punctuation(self, token: str) -> Tuple[str, str, str]:
        """
        分離音節和標點符號

        Args:
            token: 可能包含標點的音節

        Returns:
            (前置標點, 音節, 後置標點)
        """
        import re

        leading_punct = ''
        trailing_punct = ''
        syllable = token

        # 提取尾部標點
        match = re.search(r'([(),.:;—]+)$', syllable)
        if match:
            trailing_punct = match.group(1)
            syllable = syllable[:match.start()]

        # 提取開頭標點（較少見）
        match = re.search(r'^([(),.:;—]+)', syllable)
        if match:
            leading_punct = match.group(1)
            syllable = syllable[match.end():]

        return leading_punct, syllable, trailing_punct

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

        import re

        # 先將 -- 統一轉為 em-dash（向後兼容）
        original = original.replace('--', '—')

        # 使用正則表達式分割，同時保留標點符號和空格
        # 分割模式：標點符號或空格
        parts = re.split(r'(\s+|[(),.:;—]+)', original)

        # 轉換每個部分
        converted_parts = []
        for part in parts:
            if not part:
                continue
            # 判斷是否為標點符號或空格
            if re.match(r'^[\s(),.:;—]+$', part):
                # 標點或空格，保持原樣
                converted_parts.append(part)
            else:
                # 音節，進行轉換
                converted = self.convert_syllable(part)
                converted_parts.append(converted)

        return ''.join(converted_parts)
    
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

        import re

        # 選擇調型符號對應表
        tone_marks = self.SIYEN_TONE_MARKS if self.dialect == 'siyen' else self.HOILIUK_TONE_MARKS

        # 使用正則表達式分割，同時保留標點符號和空格
        parts = re.split(r'(\s+|[(),.:;—]+)', numbered)

        # 轉換每個部分
        converted_parts = []
        for part in parts:
            if not part:
                continue
            # 判斷是否為標點符號或空格
            if re.match(r'^[\s(),.:;—]+$', part):
                # 標點或空格，保持原樣
                converted_parts.append(part)
            else:
                # 音節，轉換聲調標記
                if part and part[-1].isdigit():
                    tone_number = part[-1]
                    base = part[:-1]

                    # 獲取調型符號
                    tone_mark = tone_marks.get(tone_number, '')

                    # 調型符號放在音節最後面
                    marked = base + tone_mark
                    converted_parts.append(marked)
                else:
                    # 沒有調號，保持原樣
                    converted_parts.append(part)

        return ''.join(converted_parts)
    
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

        import re

        # 先將 -- 統一轉為 em-dash（向後兼容）
        numbered = numbered.replace('--', '—')

        # 使用正則表達式分割，同時保留標點符號和空格
        parts = re.split(r'(\s+|[(),.:;—]+)', numbered)

        # 處理每個部分
        pfs_parts = []  # 儲存 (類型, 內容) 元組
        for part in parts:
            if not part:
                continue

            # 判斷是否為標點符號
            if re.match(r'^[(),.:;—]+$', part):
                pfs_parts.append(('punct', part))
            # 跳過空格（pfs 不需要保留空格，音節間用連字號連接）
            elif re.match(r'^\s+$', part):
                continue
            else:
                # 音節，轉換為 pfs
                # 提取調號（最後一個字符應該是數字）
                if part[-1].isdigit():
                    tone_number = part[-1]
                    base = part[:-1]
                else:
                    # 沒有調號，視為第3調
                    tone_number = '3'
                    base = part

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
                    pfs_parts.append(('syllable', pfs_syllable))
                else:
                    # 拆分聲母和韻母
                    initial, rhyme = self._split_syllable(base)

                    # 轉換聲母
                    pfs_initial = self.PFS_INITIAL_MAP.get(initial, initial) if initial else ''

                    # 檢查韻尾
                    # 特殊處理 nn 鼻化韻尾（轉為 ⁿ）
                    if len(rhyme) >= 2 and rhyme[-2:] == 'nn':
                        ending = 'ⁿ'
                        nucleus = rhyme[:-2]
                    # 特殊處理 ng 韻尾
                    elif len(rhyme) >= 2 and rhyme[-2:] == 'ng':
                        ending = 'ng'
                        nucleus = rhyme[:-2]
                    elif len(rhyme) > 0 and rhyme[-1] in ['b', 'd', 'g', 'm', 'n']:
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

                    pfs_parts.append(('syllable', pfs_syllable))

        # 組合結果：音節間用連字號，標點前後不加連字號
        result_parts = []
        for i, (part_type, content) in enumerate(pfs_parts):
            if part_type == 'syllable':
                # 檢查前一個是否也是音節，是的話加連字號
                if i > 0 and pfs_parts[i-1][0] == 'syllable':
                    result_parts.append('-')
                result_parts.append(content)
            elif part_type == 'punct':
                # 標點符號直接加入
                result_parts.append(content)
                # em-dash 後面不加空格，其他標點後面加空格
                if i < len(pfs_parts) - 1 and content != '—':
                    result_parts.append(' ')

        result = ''.join(result_parts)
        return unicodedata.normalize('NFC', result)

    def _convert_ipa_rhyme(self, rhyme: str) -> str:
        """
        轉換韻母為 IPA 形式

        處理：
        - ee → ɛ
        - ii → ɨ
        - oo → ɔ
        - b/d/g 韻尾 → p̚/t̚/k̚
        - ng → ŋ
        - nn → 鼻化（在元音上加 ̃）
        """
        if not rhyme:
            return ''

        # 先處理二合元音（在處理韻尾之前）
        rhyme = rhyme.replace('ee', 'ɛ')
        rhyme = rhyme.replace('ii', 'ɨ')
        rhyme = rhyme.replace('oo', 'ɔ')

        # 處理鼻化韻尾 nn
        if rhyme.endswith('nn'):
            # 移除 nn，在所有元音上加鼻化符號
            base = rhyme[:-2]
            nasalized = ''
            for char in base:
                nasalized += char
                if char in 'aeiouɛɨɔ':
                    nasalized += '\u0303'  # combining tilde
            return nasalized

        # 處理 ng 韻尾
        if rhyme.endswith('ng'):
            return rhyme[:-2] + 'ŋ'

        # 處理入聲韻尾 b/d/g
        if rhyme.endswith('b'):
            return rhyme[:-1] + 'p̚'
        elif rhyme.endswith('d'):
            return rhyme[:-1] + 't̚'
        elif rhyme.endswith('g'):
            return rhyme[:-1] + 'k̚'

        return rhyme

    def _parse_numbered_syllable(self, syllable: str) -> Tuple[str, str, str]:
        """
        解析 numbered 音節為 (聲母, 韻母, 聲調)

        Args:
            syllable: numbered 音節，例如 "sɨ1", "m5", "ngip8"

        Returns:
            (initial, rhyme, tone) 元組
        """
        if not syllable:
            return '', '', ''

        # 提取聲調（最後一個字符應該是數字）
        if syllable[-1].isdigit():
            tone = syllable[-1]
            base = syllable[:-1]
        else:
            # 沒有聲調
            return syllable, '', ''

        # 嘗試匹配聲母
        initial = ''
        for init in self.INITIALS:
            if base.startswith(init):
                initial = init
                break

        # 韻母是剩餘部分
        rhyme = base[len(initial):] if initial else base

        return initial, rhyme, tone

    def _is_syllabic_consonant(self, initial: str, rhyme: str) -> bool:
        """
        判斷是否為成音節（韻母為空，整個音節只有 m/n/ng + 聲調）
        """
        return rhyme == '' and initial in ['m', 'n', 'ng']

    def _apply_sandhi(self, syllables_data: List[Tuple[str, str, str, str]], positions: List[int]) -> List[str]:
        """
        套用變調規則

        Args:
            syllables_data: 每個音節的 (IPA聲母, IPA韻母, 原調, 原numbered音節) 列表
            positions: 每個音節在原始字串中的位置（用於判斷是否有標點分隔）

        Returns:
            每個音節的完整 IPA（含變調標記）
        """
        tone_values = self.SIYEN_TONE_VALUES if self.dialect == 'siyen' else self.HOILIUK_TONE_VALUES
        result = []

        for i, (ipa_initial, ipa_rhyme, tone, original_syllable) in enumerate(syllables_data):
            base_tone_value = tone_values.get(tone, '')

            # 判斷是否需要變調
            sandhi_tone = None

            # 檢查前一個音節（用於仔尾變調）
            has_prev = i > 0
            if has_prev and self.dialect == 'siyen':
                prev_tone = syllables_data[i - 1][2]
                # 規則2: 前字第2/4調 + 後字是 e2 → 後字讀如第5調
                if prev_tone in ['2', '4'] and original_syllable == 'e2':
                    sandhi_tone = self.SIYEN_TONE_VALUES['5']  # ¹¹

            # 檢查是否有下一個音節（且中間沒有標點分隔）
            has_next = i < len(syllables_data) - 1
            if has_next and not sandhi_tone:  # 如果還沒有變調
                next_tone = syllables_data[i + 1][2]
                next_syllable = syllables_data[i + 1][3]

                if self.dialect == 'siyen':
                    # 四縣變調規則
                    # 規則1: 前字第1調 + 後字第1/3/8調 → 前字讀如第5調
                    if tone == '1' and next_tone in ['1', '3', '8']:
                        sandhi_tone = self.SIYEN_TONE_VALUES['5']  # ¹¹

                elif self.dialect == 'hoiliuk':
                    # 海陸變調規則
                    # 規則1: 前字第2調 → 前字讀如第7調
                    if tone == '2':
                        sandhi_tone = self.HOILIUK_TONE_VALUES['7']  # ³³

                    # 規則2: 前字第4調 → 前字讀如第8調
                    elif tone == '4':
                        sandhi_tone = self.HOILIUK_TONE_VALUES['8']  # ²

            # 組合音節
            if sandhi_tone:
                # 有變調：顯示 原調-變調
                syllable_ipa = ipa_initial + ipa_rhyme + base_tone_value + '⁻' + sandhi_tone
            else:
                # 無變調
                syllable_ipa = ipa_initial + ipa_rhyme + base_tone_value

            result.append(syllable_ipa)

        return result

    def numbered_to_ipa(self, numbered: str) -> str:
        """
        將調號式客語拼音轉換為國際音標（IPA）

        Args:
            numbered: 調號式客語拼音

        Returns:
            國際音標，用 / / 包夾
        """
        if not numbered:
            return ''

        import re

        # 使用正則表達式分割，保留標點和空格信息
        parts = re.split(r'(\s+|[(),.:;—]+)', numbered)

        syllables_data = []  # (IPA聲母, IPA韻母, 原調, 原numbered音節)
        has_punct_before = [False]  # 記錄每個音節前是否有標點

        for part in parts:
            if not part:
                continue

            # 判斷是否為標點或空格
            if re.match(r'^[\s(),.:;—]+$', part):
                # 標點/空格：下一個音節前標記為有標點
                if syllables_data:
                    # 已經有音節了，下一個會有標點分隔
                    has_punct_before.append(True)
                continue

            # 音節：解析並轉換
            initial, rhyme, tone = self._parse_numbered_syllable(part)

            # 轉換聲母
            ipa_initial = self.IPA_INITIAL_MAP.get(initial, initial) if initial else ''

            # 處理成音節（m, n, ng 沒有韻母）
            if self._is_syllabic_consonant(initial, rhyme):
                # 成音節：加上成音節符號
                if initial == 'm':
                    ipa_rhyme = 'm̩'  # m + U+0329
                    ipa_initial = ''
                elif initial == 'n':
                    ipa_rhyme = 'n̩'  # n + U+0329
                    ipa_initial = ''
                elif initial == 'ng':
                    ipa_rhyme = 'ŋ̍'  # ŋ + U+030D
                    ipa_initial = ''
            else:
                # 一般音節：轉換韻母
                ipa_rhyme = self._convert_ipa_rhyme(rhyme)

            syllables_data.append((ipa_initial, ipa_rhyme, tone, part))

            # 如果這是第一個音節後的音節，且前面沒有標點
            if len(has_punct_before) == len(syllables_data):
                has_punct_before.append(False)

        # 套用變調規則（考慮標點分隔）
        # 需要重新組織，按標點分組
        groups = []
        current_group = []
        for i, data in enumerate(syllables_data):
            if i < len(has_punct_before) and has_punct_before[i] and current_group:
                # 前面有標點，開始新組
                groups.append(current_group)
                current_group = [data]
            else:
                current_group.append(data)

        if current_group:
            groups.append(current_group)

        # 對每組套用變調
        all_ipa_syllables = []
        for group in groups:
            ipa_syllables = self._apply_sandhi(group, [])
            all_ipa_syllables.extend(ipa_syllables)

        # 組合結果：用空格分隔
        if all_ipa_syllables:
            result = ' '.join(all_ipa_syllables)
            return unicodedata.normalize('NFC', result)
        else:
            return ''


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

            # 統一將 -- 轉為 em-dash（更新 original）
            original = original.replace('--', '—')
            entry['pronunciation']['original'] = original

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

            # 轉換為國際音標
            ipa = converter.numbered_to_ipa(numbered)
            if ipa:  # 只有成功轉換時才添加
                entry['pronunciation']['ipa'] = ipa

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