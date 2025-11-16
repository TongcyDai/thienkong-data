#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客語辭典解析器 - 完整版
處理《臺灣四縣腔海陸腔客家話辭典》HTML格式
支持：音節介紹、主詞條、單字詞條、多字詞條
"""

import re
import json
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path


class HakkaParser:
    def __init__(self):
        self.entries = []
        self.current_id = 1
        
    def load_html(self, html_path):
        """載入HTML文件"""
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return BeautifulSoup(content, 'html.parser')
    
    def extract_text_with_underline(self, element):
        """
        提取文本，保留下劃線標記
        例如：c<u>o</u>n → co̱n
        """
        if isinstance(element, NavigableString):
            return str(element)
        
        text = ""
        for child in element.children:
            if child.name == 'u':
                # 下劃線的內容添加組合用下劃線符號
                text += child.get_text() + '\u0331'  # 組合用下劃線
            elif isinstance(child, NavigableString):
                text += str(child)
            else:
                text += self.extract_text_with_underline(child)
        return text
    
    def clean_whitespace(self, text):
        """
        清理文本中的 \n\t：直接替換為空格
        後續會用 normalize_spaces 統一處理空格
        """
        # 將所有 \n\t 替換為單個空格
        text = re.sub(r'[\n\t]+', ' ', text)
        return text
    
    def normalize_spaces(self, text):
        """
        標準化空格：
        - 保留：字母和字母之間的空格
        - 移除：漢字和漢字之間的空格
        - 移除：漢字和字母之間的空格
        
        字母定義：拉丁字母（含變音符號）、數字、半形標點
        漢字定義：CJK字符、全形標點、假名等
        """
        import unicodedata
        
        def is_latin_like(char):
            """判斷是否為拉丁字母類（包括數字、半形標點、組合符號）"""
            if not char or char == ' ':
                return False
            
            # 檢查是否為組合用變音符號（Combining Diacritical Marks）
            # Unicode 範圍：U+0300-U+036F
            code = ord(char)
            if 0x0300 <= code <= 0x036F:
                return True
            
            try:
                name = unicodedata.name(char, '')
                # 拉丁字母（含變音符號）
                if 'LATIN' in name:
                    return True
                # 額外檢查是否包含 COMBINING
                if 'COMBINING' in name:
                    return True
            except:
                pass
            # 數字和半形標點
            if char in '0123456789.,;:!?-()[]{}\'\"':
                return True
            # 檢查是否為 ASCII 字母
            if char.isascii() and char.isalpha():
                return True
            return False
        
        def is_cjk_like(char):
            """判斷是否為CJK字符類（漢字、假名、全形標點等）"""
            if not char or char == ' ':
                return False
            try:
                name = unicodedata.name(char, '')
                # CJK字符
                if 'CJK' in name:
                    return True
                # 假名
                if 'HIRAGANA' in name or 'KATAKANA' in name:
                    return True
            except:
                pass
            # 全形標點
            if char in '，。、！？；：「」『』（）【】…—':
                return True
            # 檢查 Unicode 範圍
            code = ord(char)
            # CJK 統一表意文字
            if 0x4E00 <= code <= 0x9FFF:
                return True
            # 假名
            if 0x3040 <= code <= 0x30FF:
                return True
            return False
        
        # 處理空格
        result = []
        i = 0
        while i < len(text):
            char = text[i]
            
            if char == ' ':
                # 檢查前後字符
                before = text[i-1] if i > 0 else ''
                after = text[i+1] if i < len(text)-1 else ''
                
                before_is_latin = is_latin_like(before)
                after_is_latin = is_latin_like(after)
                
                # 只保留字母和字母之間的空格
                if before_is_latin and after_is_latin:
                    result.append(' ')
                # 否則跳過這個空格
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def clean_pronunciation(self, pron):
        """清理拼音"""
        # 先清理 \n\t
        pron = self.clean_whitespace(pron)
        
        # 移除多餘空白
        pron = re.sub(r'\s+', ' ', pron).strip()
        
        # 移除非拼音字符（保留字母、聲調符號、空格、下劃線）
        # 移除 --、／等符號
        pron = re.sub(r'-{2,}', '', pron)  # 移除--
        pron = re.sub(r'[／/]', '', pron)  # 移除斜線
        
        # 再次清理空白
        pron = re.sub(r'\s+', ' ', pron).strip()
        
        return pron
    
    # def create_searchable_pronunciation(self, pron):
    #     """創建可搜尋的拼音（無聲調）"""
    #     # 移除聲調符號
    #     tone_map = {
    #         'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
    #         'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
    #         'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
    #         'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
    #         'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
    #         'ń': 'n', 'ň': 'n', 'ǹ': 'n',
    #         'ḿ': 'm', 'ň': 'n',
    #     }
    #     
    #     searchable = pron
    #     for accented, plain in tone_map.items():
    #         searchable = searchable.replace(accented, plain)
    #     
    #     # 移除組合用下劃線
    #     searchable = searchable.replace('\u0331', '')
    #     
    #     return searchable.lower()
    
    def split_by_marker(self, text):
        """
        依據標記符號分割釋義和例句
        標記包括：
        - 📌 (例句標記，原 U+E738)
        - ⚫ (例句標記)
        - ①②③... (定義編號，原 U+E897-U+E8A9)
        - ❶❷❸... (定義編號，原 U+F08C-U+F095)
        - 又、再 (引申義標記)
        """
        examples = []
        main_def = text
        
        # 優先處理 📌 例句標記
        if '📌' in text:
            parts = text.split('📌')
            main_def = parts[0].strip()
            examples = [s.strip() for s in parts[1:] if s.strip()]
            return main_def, examples
        
        # 處理 ⚫ 標記
        if '⚫' in text:
            parts = text.split('⚫')
            main_def = parts[0].strip()
            examples = [s.strip() for s in parts[1:] if s.strip()]
            return main_def, examples
        
        # 如果沒有明確標記，嘗試用其他模式識別例句
        # 例句特徵：包含「！」「？」「嚒」等口語標記
        sentences = text.split('。')
        
        if len(sentences) > 1:
            last_sentence = sentences[-1].strip()
            if last_sentence and any(marker in last_sentence for marker in ['！', '？', '嚒', '啦', '哦', '呢']):
                main_def = '。'.join(sentences[:-1]) + '。'
                examples = [last_sentence]
        
        return main_def.strip(), examples
    
    def split_definitions(self, text):
        """
        分割多義詞的多個定義，保留 marker 資訊
        定義編號標記：①②③...⑲ (原 U+E897-U+E8A9)
        特殊編號標記：❶❷❸...❿ (原 U+F08C-U+F095)
        
        返回格式：[{'marker': '①', 'text': '...'}, ...]
        """
        # 定義編號字符集
        circled_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲'
        filled_circles = '❶❷❸❹❺❻❼❽❾❿'
        all_markers = circled_numbers + filled_circles
        
        # 檢查是否包含定義編號
        has_markers = any(marker in text for marker in all_markers)
        
        if not has_markers:
            # 沒有編號，返回單一定義（marker 為 None）
            return [{'marker': None, 'text': text}]
        
        # 用正則表達式分割，保留標記
        pattern = f'([{all_markers}])'
        parts = re.split(pattern, text)
        
        definitions = []
        current_marker = None
        current_text = ""
        
        for part in parts:
            if part in all_markers:
                # 儲存前一段
                if current_text.strip():
                    definitions.append({
                        'marker': current_marker,
                        'text': current_text.strip()
                    })
                current_marker = part
                current_text = ""
            else:
                current_text += part
        
        # 保存最後一段
        if current_text.strip():
            definitions.append({
                'marker': current_marker,
                'text': current_text.strip()
            })
        
        return definitions if definitions else [{'marker': None, 'text': text}]
    
    def extract_inline_notes(self, text):
        """
        記錄括號內的註釋，但不從 text 中移除
        返回：(原文text, inline_notes列表)
        """
        # 提取所有括號內容
        pattern_paren = r'[（(]([^）)]+)[）)]'
        inline_notes = re.findall(pattern_paren, text)
        
        # text 保持不變
        return text, inline_notes
    
    def is_syllable_intro(self, para):
        """
        判斷是否為音節介紹
        特徵：
        1. 以小字體 (size="2" 或 11pt) 的單字母/音節開頭
        2. 包含「客語」「單元音」「韻母」等關鍵詞
        3. 內容較長（通常超過50字）
        """
        text = para.get_text().strip()
        
        # 太短不可能是音節介紹
        if len(text) < 50:
            return False
        
        # 檢查第一個字體標籤
        first_font = para.find('font', face=re.compile(r'Times New Roman'))
        if not first_font:
            return False
        
        size = first_font.get('size', '2')
        if size not in ['2', '11pt']:
            return False
        
        first_text = first_font.get_text().strip()
        
        # 檢查是否為單字母或短音節
        if len(first_text) > 5:
            return False
        
        # 檢查關鍵詞
        keywords = ['客語', '單元音', '韻母', '韻尾', '聲母', '國際音標', '注音符號']
        if any(keyword in text for keyword in keywords):
            return True
        
        return False
    
    def is_headword(self, para):
        """
        判斷是否為主詞條
        特徵：
        1. 大字體 (size="4" 或 14pt)
        2. 斜體 + 粗體 (<i><b>)
        3. Times New Roman字體（拼音）
        4. 後接華康中黑體的漢字列表
        """
        # 尋找大字體的斜體粗體拼音
        for font_tag in para.find_all('font', size=re.compile(r'^(4|14pt)$')):
            if font_tag.find('i') and font_tag.find('b'):
                # 檢查字體是否為 Times New Roman
                face = font_tag.get('face', '')
                if 'Times New Roman' in face or not face:
                    return True
        return False
    
    def is_character_entry(self, para):
        """
        判斷是否為單字詞條
        特徵：
        1. 以粗體單個漢字開頭 <b>X</b>
        2. 後接小字括號 <font size="1">(...)</font>
        
        注意：不檢查括號內容，因為並非所有字都有古字典資訊
        （如「氰」只有「北京話借用字，客語沿用」）
        """
        text = para.get_text().strip()
        
        # 尋找段落開頭的粗體標籤
        first_bold = None
        for child in para.children:
            if isinstance(child, NavigableString):
                if child.strip():
                    break
            elif child.name == 'b' or (child.name == 'font' and child.find('b')):
                first_bold = child
                break
            elif child.name == 'font':
                first_bold_in_font = child.find('b')
                if first_bold_in_font:
                    first_bold = first_bold_in_font
                    break
        
        if not first_bold:
            return False
        
        # 檢查粗體內容是否為單個漢字
        bold_text = first_bold.get_text().strip()
        if len(bold_text) != 1:
            return False
        
        # 檢查是否有小字括號
        small_fonts = para.find_all('font', size=re.compile(r'^(1|8pt)$'))
        if not small_fonts:
            return False
        
        # 只要有粗體單字 + 小字體標籤，就認為是 character entry
        # 不再檢查括號內容是否包含特定關鍵詞
        return True
    
    def parse_syllable_intro(self, para):
        """
        解析音節介紹
        返回格式：
        {
            'type': 'syllable_intro',
            'syllable': 'a',
            'description': '客語七個單元音...',
            'sections': [
                {'marker': '①', 'text': '...', 'examples': [...]},
                ...
            ]
        }
        """
        # 提取音節（第一個Times New Roman字體）
        first_font = para.find('font', face=re.compile(r'Times New Roman'))
        if not first_font:
            return None
        
        syllable = first_font.get_text().strip()
        
        # 提取完整描述文本
        full_text = para.get_text().strip()
        
        # 移除開頭的音節部分
        description = full_text.replace(syllable, '', 1).strip()
        
        # 分割為不同段落（根據 ①②③ 標記）
        section_parts = self.split_definitions(description)
        
        sections = []
        for part in section_parts:
            text = part['text']
            marker = part['marker']
            
            # 提取例句
            main_text, examples = self.split_by_marker(text)
            
            sections.append({
                'marker': marker,
                'text': main_text,
                'examples': examples
            })
        
        entry = {
            'id': str(self.current_id),
            'type': 'syllable_intro',
            'syllable': syllable,
            'description': sections[0]['text'] if sections and not sections[0]['marker'] else description,
            'sections': sections if len(sections) > 1 or sections[0].get('marker') else []
        }
        
        self.current_id += 1
        return entry
    
    def parse_headword(self, para):
        """
        解析主詞條
        返回格式：
        {
            'type': 'headword',
            'pronunciation': 'ā',
            'characters': ['阿', '啊'],
            'create_character_entries': True  # 標記需要為每個字符創建entry
        }
        """
        # 提取拼音（大字體斜體粗體）- 可能跨越多個 font 標籤
        pronunciation_parts = []
        for font_tag in para.find_all('font', size=re.compile(r'^(4|14pt)$')):
            if font_tag.find('i') and font_tag.find('b'):
                part = self.extract_text_with_underline(font_tag)
                pronunciation_parts.append(part)
        
        if not pronunciation_parts:
            return None
        
        # 合併所有部分（處理跨多個 font 標籤的拼音，如 p + a̱）
        pronunciation = ''.join(pronunciation_parts)
        pronunciation = self.clean_pronunciation(pronunciation)
        
        # 提取漢字列表（華康中黑體或華康粗黑體）
        characters = []
        for font_tag in para.find_all('font', face=re.compile(r'華康.*黑體')):
            bold_tag = font_tag.find('b')
            if bold_tag:
                chars = bold_tag.get_text().strip()
                # 將連續漢字拆分為單個字符
                characters.extend(list(chars))
        
        # 去重但保持順序
        seen = set()
        characters = [c for c in characters if c not in seen and not seen.add(c)]
        
        entry = {
            'id': str(self.current_id),
            'type': 'headword',
            'pronunciation': {
                'original': pronunciation
            },
            'characters': characters,
            'create_character_entries': True  # 標記
        }
        
        self.current_id += 1
        return entry
    
    def find_recent_character_entry(self, character, pronunciation):
        """
        查找最近添加的匹配字符entry（從後往前找）
        只查找沒有classical_notes的基礎entry（即從headword創建的）
        """
        # 標準化pronunciation進行比較（只比較字符串值）
        search_pron = pronunciation if isinstance(pronunciation, str) else pronunciation
        
        for i in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[i]
            if entry['type'] != 'character':
                continue
            
            if entry['character'] != character:
                continue
            
            # 比較發音（新結構都是字典）
            entry_pron_dict = entry.get('pronunciation', {})
            if isinstance(entry_pron_dict, dict):
                entry_pron = entry_pron_dict.get('original', '')
            else:
                # 向後兼容（舊數據可能是字符串）
                entry_pron = entry_pron_dict
            
            if entry_pron == search_pron:
                # 只更新沒有詳細資訊的entry（從headword創建的基礎entry）
                if not entry.get('classical_notes'):
                    return i
        
        return None
    
    def extract_reading_notes(self, text):
        """
        提取「讀音作」和「語音作」資訊
        返回：(literary_reading, vernacular_reading)
        """
        literary = None
        vernacular = None
        
        # 提取「讀音作」（表示目前是白讀，XXX是文讀）
        literary_match = re.search(r'讀音作[「『]([^」』]+)[」』]', text)
        if literary_match:
            literary = literary_match.group(1).strip()
        
        # 提取「語音作」（表示目前是文讀，XXX是白讀）
        vernacular_match = re.search(r'語音作[「』]([^」』]+)[」』]', text)
        if vernacular_match:
            vernacular = vernacular_match.group(1).strip()
        
        return literary, vernacular
    
    def parse_character_entry(self, para):
        """
        解析單字詞條
        返回格式：
        {
            'type': 'character',
            'pronunciation': 'ā',
            'character': '阿',
            'classical_notes': '源自北京話音',
            'literary_reading': None,
            'vernacular_reading': None,
            'definitions': [...]
        }
        """
        # 提取單個漢字（第一個粗體）
        character = ""
        first_bold = None
        for child in para.children:
            if isinstance(child, NavigableString):
                if child.strip():
                    break
            elif child.name == 'b':
                first_bold = child
                break
            elif child.name == 'font':
                first_bold = child.find('b')
                if first_bold:
                    break
        
        if not first_bold:
            return None
        
        character = first_bold.get_text().strip()
        
        # 提取括號內的古字典資訊
        # 從整個段落文本中提取（因為括號可能在不同的font標籤中）
        full_text = para.get_text()
        classical_notes = None
        
        # 尋找粗體字後面的括號內容
        # 先定位到字符位置，然後尋找其後的括號
        char_pos = full_text.find(character)
        if char_pos != -1:
            # 從字符後面開始尋找括號
            text_after_char = full_text[char_pos + len(character):]
            # 匹配括號內容（支持中英文括號）
            match = re.search(r'[（(]([^）)]+)[）)]', text_after_char)
            if match:
                classical_notes = match.group(1).strip()
        
        # 提取讀音作/語音作
        literary_reading, vernacular_reading = self.extract_reading_notes(full_text)
        
        # TODO: 提取定義（在後續段落中，以 ①②③ 或縮排標記開始）
        # 這部分需要在主parse函數中處理上下文關係
        
        entry = {
            'id': None,  # ID 在主函數中設置
            'type': 'character',
            'pronunciation': None,  # 在主函數中設置為字典結構
            'character': character,
            'classical_notes': classical_notes if classical_notes else None,
            'literary_reading': literary_reading,
            'vernacular_reading': vernacular_reading,
            'definitions': []  # 需要從後續段落提取
        }
        
        # 不在這裡增加 current_id，由調用者決定
        return entry
    
    def is_cjk_char(self, char):
        """
        判斷是否為 CJK 字符（漢字）
        包含所有中日韓統一表意文字及相關區域
        """
        if not char:
            return False
        
        code = ord(char)
        
        # 完整的 CJK Unicode 範圍
        cjk_ranges = [
            (0x3000, 0x303F),    # 中日韓符號和標點
            (0x3400, 0x4DBF),    # 中日韓統一表意文字擴充區A
            (0x4E00, 0x9FFF),    # 中日韓統一表意文字（基本區）
            (0xE000, 0xF8FF),    # 私用區
            (0xF900, 0xFAFF),    # 中日韓相容表意文字
            (0xFE30, 0xFE4F),    # 中日韓相容形式
            (0x20000, 0x2A6DF),  # 中日韓統一表意文字擴充區B
            (0x2A700, 0x2B73F),  # 中日韓統一表意文字擴充區C
            (0x2B740, 0x2B81F),  # 中日韓統一表意文字擴充區D
            (0x2B820, 0x2CEAF),  # 中日韓統一表意文字擴充區E
            (0x2CEB0, 0x2EBEF),  # 中日韓統一表意文字擴充區F
            (0x2EBF0, 0x2EE5F),  # 中日韓統一表意文字擴充區I
            (0x2F800, 0x2FA1F),  # 中日韓相容表意文字補充區
            (0x30000, 0x3134F),  # 中日韓統一表意文字擴充區G
            (0x31350, 0x323AF),  # 中日韓統一表意文字擴充區H
            (0x323B0, 0x3347F),  # 中日韓統一表意文字擴充區J
        ]
        
        for start, end in cjk_ranges:
            if start <= code <= end:
                return True
        
        return False
    
    def find_first_cjk_char(self, text):
        """
        找第一個 CJK 字符（漢字）的位置
        返回：位置索引，如果沒有則返回 None
        """
        for i, char in enumerate(text):
            if self.is_cjk_char(char):
                return i
        return None
    
    def is_definition_para(self, para):
        """
        判斷是否為定義段落
        特徵：
        1. 有縮排 (margin-left)
        2. 以 ①②③ 等標記開頭
        """
        style = para.get('style', '')
        
        # 檢查縮排
        if 'margin-left' in style or 'text-indent' in style:
            return True
        
        # 檢查是否以編號標記開頭
        text = para.get_text().strip()
        circled_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲'
        filled_circles = '❶❷❸❹❺❻❼❽❾❿'
        
        if text and text[0] in (circled_numbers + filled_circles):
            return True
        
        return False
    
    def parse_compound_entry(self, para):
        """
        解析複合詞條（多字詞）
        格式：
        1. 拼音 漢字＝釋義
        2. 拼音 ①釋義（無漢字外來語）
        3. 拼音 漢字定義（無等號，如：sā ku là 櫻花，源自...）
        
        改進策略：
        - 使用完整文本提取（而非只取第一個 font 標籤）
        - 正確處理跨多個標籤的拼音（如 sā bbì si̱i）
        - 基於第一個漢字位置來分割拼音和 headword
        """
        # 1. 使用 extract_text_with_underline 提取完整段落文本（處理下劃線）
        full_text = self.extract_text_with_underline(para)
        full_text = self.clean_whitespace(full_text)
        
        # 跳過太短的段落
        if len(full_text.strip()) < 5:
            return None
        
        # 2. 檢查是否包含拼音（拉丁字母）
        has_latin = any(c.isalpha() or c in 'āáǎàēéěèīíǐìōóǒòūúǔùńňǹḿ\u0331' for c in full_text)
        if not has_latin:
            return None
        
        # 3. 找第一個 CJK 字符（漢字）的位置
        first_cjk_pos = self.find_first_cjk_char(full_text)
        
        # 4. 判斷詞條格式並分割
        pronunciation = ""
        headword = ""
        definition_text = ""
        
        if '＝' in full_text or '=' in full_text:
            # 格式1：有等號的詞條
            # 例：zụt sí 椊死＝...
            # 例：sā ku là ha sā ku là 蝦＝...
            full_text = full_text.replace('=', '＝')
            
            parts = full_text.split('＝', 1)
            if len(parts) != 2:
                return None
            
            before_eq = parts[0].strip()
            definition_text = parts[1].strip()
            
            if first_cjk_pos is not None and first_cjk_pos < len(before_eq):
                # 有漢字在等號前
                # 使用「單位數」分析方法：音節+漢字的總數除以2
                # 例如：sā ku là ha sā ku là蝦
                # 7個音節 + 1個漢字 = 8個單位，除以2 = 4
                # 前4個單位（sā ku là ha）= pronunciation
                # 後4個單位（sā ku là 蝦）= headword
                
                # 1. 分析文本，提取所有單位（音節和漢字）
                units = []  # 單位列表：{'type': 'syllable'/'cjk', 'text': '...', 'start': 0, 'end': 0}
                current_syllable = ""
                syllable_start = 0
                
                for i, char in enumerate(before_eq):
                    if self.is_cjk_char(char):
                        # 遇到漢字，先保存當前音節（如果有）
                        if current_syllable:
                            units.append({
                                'type': 'syllable',
                                'text': current_syllable,
                                'start': syllable_start,
                                'end': i
                            })
                            current_syllable = ""
                        # 添加漢字單位
                        units.append({
                            'type': 'cjk',
                            'text': char,
                            'start': i,
                            'end': i + 1
                        })
                    elif char.isalpha() or char in 'āáǎàēéěèīíǐìōóǒòūúǔùńňǹḿ\u0331':
                        # 拉丁字母
                        if not current_syllable:
                            syllable_start = i
                        current_syllable += char
                    elif char == ' ':
                        # 空格分隔音節
                        if current_syllable:
                            units.append({
                                'type': 'syllable',
                                'text': current_syllable,
                                'start': syllable_start,
                                'end': i
                            })
                            current_syllable = ""
                
                # 處理最後一個音節
                if current_syllable:
                    units.append({
                        'type': 'syllable',
                        'text': current_syllable,
                        'start': syllable_start,
                        'end': len(before_eq)
                    })
                
                # 2. 計算總單位數並找分割點
                total_units = len(units)
                
                if total_units >= 2:
                    # 檢查是否有重複結構（音節數明顯多於漢字數）
                    num_syllables = sum(1 for u in units if u['type'] == 'syllable')
                    num_cjk = sum(1 for u in units if u['type'] == 'cjk')
                    
                    # 如果音節數 > 漢字數 * 2，可能有重複結構
                    if num_syllables > num_cjk * 2 and num_cjk > 0:
                        # 使用「總單位數除以2」的方法
                        split_unit_index = total_units // 2
                        
                        # 找到分割位置（第 split_unit_index 個單位的結束位置）
                        if split_unit_index < total_units:
                            split_pos = units[split_unit_index - 1]['end']
                            
                            pronunciation = before_eq[:split_pos].strip()
                            headword = before_eq[split_pos:].strip()
                        else:
                            # 不應該到這裡，使用備用方法
                            last_space = before_eq[:first_cjk_pos].rfind(' ')
                            if last_space != -1:
                                pronunciation = before_eq[:last_space].strip()
                                headword = before_eq[last_space+1:].strip()
                            else:
                                pronunciation = before_eq[:first_cjk_pos].strip()
                                headword = before_eq[first_cjk_pos:].strip()
                    else:
                        # 沒有明顯的重複結構，使用簡單方法：第一個漢字前的最後一個空格
                        text_before_cjk = before_eq[:first_cjk_pos]
                        last_space = text_before_cjk.rfind(' ')
                        
                        if last_space != -1:
                            pronunciation = before_eq[:last_space].strip()
                            headword = before_eq[last_space+1:].strip()
                        else:
                            # 沒有空格，拉丁字母直接連著漢字（如 là蝦）
                            # 從第一個漢字往前找連續的拉丁字母段
                            latin_start = first_cjk_pos
                            while latin_start > 0 and (before_eq[latin_start-1].isalpha() or before_eq[latin_start-1] in 'āáǎàēéěèīíǐìōóǒòūúǔùńňǹḿ\u0331'):
                                latin_start -= 1
                            
                            if latin_start > 0:
                                pronunciation = before_eq[:latin_start].strip()
                                headword = before_eq[latin_start:].strip()
                            else:
                                # 整個等號前都是拉丁+漢字
                                pronunciation = ""
                                headword = before_eq
                else:
                    # 單位數太少
                    pronunciation = ""
                    headword = before_eq
            else:
                # 等號前沒有漢字（純拉丁字母 headword）
                # 這種情況較少見，暫時當作外來語處理
                pronunciation = before_eq
                headword = before_eq
        
        else:
            # 沒有等號的情況
            circled_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲'
            filled_circles = '❶❷❸❹❺❻❼❽❾❿'
            all_markers = circled_numbers + filled_circles
            
            if full_text and full_text[0] in all_markers:
                # 格式2：拼音 ①定義（無漢字外來語，以編號開頭）
                # 需要從 para 中提取拼音部分
                # 找第一個小字體 font 作為拼音
                pron_from_font = ""
                for font_tag in para.find_all('font'):
                    size = font_tag.get('size', '')
                    if size in ['2', '11pt', '9pt']:
                        font_text = font_tag.get_text().strip()
                        if font_text and any(c.isalpha() or c in 'āáǎàēéěèīíǐìōóǒòūúǔùńňǹḿ' for c in font_text):
                            pron_from_font = self.extract_text_with_underline(font_tag)
                            break
                
                if pron_from_font:
                    pronunciation = self.clean_pronunciation(pron_from_font)
                    headword = pronunciation
                    definition_text = full_text
                else:
                    return None
                
            elif first_cjk_pos is not None:
                # 格式3：拼音 漢字，定義（無等號、有漢字）
                # 例：sā ku là 櫻花，源自...
                # 例：sā bbì si̱i 招待、意思意思。源自...
                
                # 第一個漢字之前的所有內容是拼音
                pronunciation = full_text[:first_cjk_pos].strip()
                pronunciation = self.clean_pronunciation(pronunciation)
                
                # headword 使用拼音（因為沒有明確的 headword 標記）
                headword = pronunciation
                
                # 定義是從第一個漢字開始
                definition_text = full_text[first_cjk_pos:].strip()
            else:
                # 純拉丁字母，無漢字，無編號標記
                # 檢查是否包含定義特徵
                has_definition_keywords = any(kw in full_text for kw in ['源自', '又作', '意思', '屬於', '，'])
                
                if has_definition_keywords:
                    # 當作外來語詞條
                    # 嘗試從文本中分離拼音部分
                    # 找第一個小字體 font
                    pron_from_font = ""
                    for font_tag in para.find_all('font'):
                        size = font_tag.get('size', '')
                        if size in ['2', '11pt', '9pt']:
                            font_text = font_tag.get_text().strip()
                            if font_text and any(c.isalpha() or c in 'āáǎàēéěèīíǐìōóǒòūúǔùńňǹḿ' for c in font_text):
                                pron_from_font = self.extract_text_with_underline(font_tag)
                                break
                    
                    if pron_from_font:
                        pronunciation = self.clean_pronunciation(pron_from_font)
                        headword = pronunciation
                        # 從 full_text 中移除拼音部分得到定義
                        pron_text_clean = self.clean_whitespace(pron_from_font)
                        definition_text = full_text.replace(pron_text_clean, '', 1).strip()
                    else:
                        return None
                else:
                    # 不是詞條
                    return None
        
        # 5. 驗證結果
        if not pronunciation or not headword:
            return None
        
        # 6. 清理多餘的空白
        definition_text = re.sub(r'\s+', ' ', definition_text).strip()
        
        # 7. 分割多個定義（如果有編號標記）
        definition_parts = self.split_definitions(definition_text)
        
        # 8. 處理每個定義
        definitions = []
        for def_dict in definition_parts:
            def_text = def_dict['text']
            marker = def_dict['marker']
            
            # 分離主釋義和例句
            main_def, examples = self.split_by_marker(def_text)
            
            # 提取 inline_notes
            main_def, inline_notes = self.extract_inline_notes(main_def)
            
            definitions.append({
                'marker': marker,
                'text': main_def,
                'examples': examples,
                'inline_notes': inline_notes
            })
        
        # 9. 識別來源
        source = None
        first_def = definition_parts[0]['text'] if definition_parts else definition_text
        if '源自' in first_def:
            source_match = re.search(r'源自([^。，]+)', first_def)
            if source_match:
                source = source_match.group(1).strip()
        
        # 10. 識別別稱
        variants = []
        if '又作' in definition_text:
            variant_matches = re.findall(r'又作[「『]([^」』]+)[」』]', definition_text)
            variants.extend(variant_matches)
        
        # 11. 創建詞條資料
        entry = {
            'id': str(self.current_id),
            'type': 'word',
            'pronunciation': {
                'original': pronunciation
            },
            'headword': headword,
            'definitions': definitions,
            'source': source,
            'variants': variants
        }
        
        self.current_id += 1
        return entry
    
    def parse(self, html_path):
        """解析整個HTML文件"""
        soup = self.load_html(html_path)
        
        # 找到主要內容區域
        main_section = soup.find('div', id='TextSection')
        if not main_section:
            print("警告：未找到主要內容區域")
            return []
        
        # 遍歷所有段落
        paragraphs = main_section.find_all('p')
        print(f"找到 {len(paragraphs)} 個段落")
        
        current_pronunciation = None  # 用於追蹤當前的拼音（給character用）
        pending_character_entry = None  # 待補充definitions的character entry
        
        for i, para in enumerate(paragraphs):
            # 1. 音節介紹 - 已移除，當作普通詞條處理
            # if self.is_syllable_intro(para):
            #     ...
            
            # 2. 主詞條
            if self.is_headword(para):
                # 結束之前的character entry處理
                pending_character_entry = None
                
                entry = self.parse_headword(para)
                if entry:
                    self.entries.append(entry)
                    current_pronunciation = entry['pronunciation']['original']
                    
                    # 為headword中的每個字符創建基礎character entry
                    if entry.get('create_character_entries'):
                        for char in entry['characters']:
                            char_entry = {
                                'id': str(self.current_id),
                                'type': 'character',
                                'pronunciation': {
                                    'original': current_pronunciation
                                },
                                'character': char,
                                'classical_notes': None,
                                'literary_reading': None,
                                'vernacular_reading': None,
                                'definitions': []
                            }
                            self.entries.append(char_entry)
                            self.current_id += 1
                    
                    if len(self.entries) % 50 == 0:
                        print(f"已解析 {len(self.entries)} 個條目...")
                continue
            
            # 3. 單字詞條（詳細的，有古字典資訊）
            if self.is_character_entry(para):
                entry = self.parse_character_entry(para)
                if entry:
                    # 設置pronunciation為字典結構
                    if current_pronunciation:
                        entry['pronunciation'] = {
                            'original': current_pronunciation
                        }
                    else:
                        entry['pronunciation'] = {
                            'original': ""
                        }
                    
                    # 檢查是否已存在基礎entry（從headword創建的）
                    existing_idx = self.find_recent_character_entry(
                        entry['character'], 
                        current_pronunciation
                    )
                    
                    if existing_idx is not None:
                        # 更新現有的基礎entry
                        self.entries[existing_idx].update({
                            'classical_notes': entry['classical_notes'],
                            'literary_reading': entry['literary_reading'],
                            'vernacular_reading': entry['vernacular_reading']
                        })
                        # 保留對這個entry的引用，以便後續添加definitions
                        pending_character_entry = self.entries[existing_idx]
                    else:
                        # 沒有找到基礎entry，創建新的（可能是沒有headword的獨立字）
                        entry['id'] = str(self.current_id)
                        self.current_id += 1
                        self.entries.append(entry)
                        pending_character_entry = entry
                    
                    if len(self.entries) % 50 == 0:
                        print(f"已解析 {len(self.entries)} 個條目...")
                continue
            
            # 4. 定義段落（屬於前一個character entry）
            if pending_character_entry and self.is_definition_para(para):
                text = para.get_text().strip()
                text = self.clean_whitespace(text)
                
                # 先提取開頭的編號標記（如果有）
                marker = None
                circled_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲'
                filled_circles = '❶❷❸❹❺❻❼❽❾❿'
                all_markers = circled_numbers + filled_circles
                
                if text and text[0] in all_markers:
                    marker = text[0]
                    text = text[1:].strip()  # 移除marker
                
                # 分離定義和例句
                main_def, examples = self.split_by_marker(text)
                main_def, inline_notes = self.extract_inline_notes(main_def)
                
                pending_character_entry['definitions'].append({
                    'marker': marker,
                    'text': main_def,
                    'examples': examples,
                    'inline_notes': inline_notes
                })
                continue
            
            # 5. 多字詞條
            entry = self.parse_compound_entry(para)
            if entry:
                # 當遇到新的word entry時，結束之前的character entry處理
                pending_character_entry = None
                
                self.entries.append(entry)
                
                # 每100個詞條顯示進度
                if len(self.entries) % 100 == 0:
                    print(f"已解析 {len(self.entries)} 個條目...")
        
        print(f"\n總共解析出 {len(self.entries)} 個條目")
        return self.entries
    
    def clean_all_text_fields(self):
        """
        在保存前統一清理所有文本欄位中的 \\n\\t 並標準化空格
        遍歷所有 entries，清理所有字符串類型的值
        """
        def clean_value(value):
            """遞歸清理值"""
            if isinstance(value, str):
                # 先清理 \n\t，再標準化空格
                value = self.clean_whitespace(value)
                value = self.normalize_spaces(value)
                return value
            elif isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [clean_value(item) for item in value]
            else:
                return value
        
        print("\n清理文本中的 \\n\\t 並標準化空格...")
        for entry in self.entries:
            for key, value in entry.items():
                entry[key] = clean_value(value)
        print("清理完成")
    
    def save_json(self, output_path):
        """保存為JSON格式"""
        # 在保存前統一清理所有 \n\t
        self.clean_all_text_fields()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(self.entries),
                'entries': self.entries
            }, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {output_path}")
    
    def print_sample(self, n=5):
        """顯示前N個條目的樣本"""
        print(f"\n=== 顯示前 {n} 個條目 ===\n")
        for entry in self.entries[:n]:
            entry_type = entry['type']
            print(f"類型: {entry_type}")
            
            # syllable_intro 類型已移除
            # if entry_type == 'syllable_intro':
            #     print(f"音節: {entry['syllable']}")
            #     print(f"描述: {entry['description'][:100]}...")
            
            if entry_type == 'headword':
                print(f"拼音: {entry['pronunciation']['original']}")
                print(f"漢字: {', '.join(entry['characters'])}")
            
            elif entry_type == 'character':
                pron = entry['pronunciation']
                if isinstance(pron, dict):
                    pron_str = pron.get('original', '')
                else:
                    pron_str = pron  # 向後兼容
                print(f"拼音: {pron_str}")
                print(f"漢字: {entry['character']}")
                if entry['classical_notes']:
                    print(f"古字典: {entry['classical_notes'][:80]}...")
                if entry['literary_reading']:
                    print(f"文讀: {entry['literary_reading']}")
                if entry['vernacular_reading']:
                    print(f"白讀: {entry['vernacular_reading']}")
                if entry['definitions']:
                    print(f"定義數: {len(entry['definitions'])}")
            
            elif entry_type == 'word':
                print(f"拼音: {entry['pronunciation']['original']}")
                print(f"詞條: {entry['headword']}")
                
                # 顯示所有定義
                for i, definition in enumerate(entry['definitions'], 1):
                    marker = definition.get('marker')
                    marker_str = f"[{marker}] " if marker else ""
                    
                    if len(entry['definitions']) > 1:
                        print(f"定義 {i}: {marker_str}{definition['text'][:80]}...")
                    else:
                        print(f"釋義: {marker_str}{definition['text'][:80]}...")
                    
                    if definition['examples']:
                        print(f"  例句: {definition['examples'][0][:60]}...")
            
            print("-" * 60)
    
    def print_statistics(self):
        """顯示統計資訊"""
        print("\n=== 統計資訊 ===")
        print(f"總條目數: {len(self.entries)}")
        
        # 按類型統計
        type_counts = {}
        for entry in self.entries:
            entry_type = entry['type']
            type_counts[entry_type] = type_counts.get(entry_type, 0) + 1
        
        print("\n按類型統計:")
        for entry_type, count in sorted(type_counts.items()):
            percentage = count / len(self.entries) * 100
            print(f"  {entry_type}: {count} ({percentage:.1f}%)")
        
        # 詞條統計
        word_entries = [e for e in self.entries if e['type'] == 'word']
        if word_entries:
            with_examples = sum(1 for e in word_entries 
                               if any(d['examples'] for d in e['definitions']))
            print(f"\n多字詞條統計:")
            print(f"  總數: {len(word_entries)}")
            print(f"  有例句: {with_examples} ({with_examples/len(word_entries)*100:.1f}%)")
            
            multi_def = sum(1 for e in word_entries if len(e['definitions']) > 1)
            print(f"  多義詞: {multi_def} ({multi_def/len(word_entries)*100:.1f}%)")
        
        # 單字詞條統計
        char_entries = [e for e in self.entries if e['type'] == 'character']
        if char_entries:
            with_classical = sum(1 for e in char_entries if e.get('classical_notes'))
            with_defs = sum(1 for e in char_entries if e.get('definitions'))
            print(f"\n單字詞條統計:")
            print(f"  總數: {len(char_entries)}")
            print(f"  有古字典註: {with_classical} ({with_classical/len(char_entries)*100:.1f}%)")
            print(f"  有定義: {with_defs} ({with_defs/len(char_entries)*100:.1f}%)")


def main():
    """主程式"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python hakka_parser_enhanced.py <HTML檔案路徑> [輸出JSON路徑]")
        print("例如: python hakka_parser_enhanced.py 海陸腔辭典.html output.json")
        sys.exit(1)
    
    html_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'hakka_dict_enhanced.json'
    
    # 檢查檔案是否存在
    if not Path(html_path).exists():
        print(f"錯誤：找不到檔案 {html_path}")
        sys.exit(1)
    
    # 解析
    parser = HakkaParser()
    entries = parser.parse(html_path)
    
    # 顯示樣本
    parser.print_sample(10)
    
    # 保存
    parser.save_json(output_path)
    
    # 統計
    parser.print_statistics()


if __name__ == '__main__':
    main()