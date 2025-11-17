import re
from collections import Counter

def translate_pua_to_standard(input_file, output_file):
    # Define a mapping from PUA code points to standard Unicode characters
    pua_to_standard_map = {
        '\uE897': '①',
        # list others for me
        '\uE898': '②',
        '\uE899': '③',
        '\uE89A': '④',
        '\uE89B': '⑤',
        '\uE89C': '⑥',
        '\uE89D': '⑦',
        '\uE89E': '⑧',
        '\uE89F': '⑨',
        '\uE8A0': '⑩',
        '\uE8A1': '⑪',
        '\uE8A2': '⑫',
        '\uE8A3': '⑬',
        '\uE8A4': '⑭',
        '\uE8A5': '⑮',
        '\uE8A6': '⑯',
        '\uE8A7': '⑰',
        '\uE8A8': '⑱',
        '\uE8A9': '⑲',
        '\uF08C': '❶',
        '\uF08D': '❷',
        '\uF08E': '❸',
        '\uF08F': '❹',
        '\uF090': '❺',
        '\uF091': '❻',
        '\uF092': '❼',
        '\uF093': '❽',
        '\uF094': '❾',
        '\uF095': '❿',
        '\uE738': '📌',
        '\uE4EA': '𠊎',
        '\uE442': '𠊎',
        '\uE6F1': '𫣆',
        '\uE791': '𢇗',
        '\uE7EA': '𠚺',
        '\uE7EB': '𣣺',
        '\uE5E7': '閯',
        # Add more mappings as needed
    }

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as infile:
        content = infile.read()

    # Define PUA range (U+E000 to U+F8FF)
    def is_pua_char(char):
        """Check if a character is in the basic PUA range"""
        code_point = ord(char)
        return 0xE000 <= code_point <= 0xF8FF

    # Count original PUA characters
    original_pua_chars = [char for char in content if is_pua_char(char)]
    original_pua_counter = Counter(original_pua_chars)
    original_unique_count = len(original_pua_counter)
    original_total_count = len(original_pua_chars)

    # Function to replace PUA characters with standard characters
    def replace_pua(match):
        char = match.group(0)
        return pua_to_standard_map.get(char, char)  # Return the mapped character or the original if not found

    # Create a regex pattern to match all PUA characters in the mapping
    pua_pattern = re.compile('|'.join(re.escape(key) for key in pua_to_standard_map.keys()))

    # Replace PUA characters in the content
    new_content = pua_pattern.sub(replace_pua, content)

    # Count remaining PUA characters after replacement
    remaining_pua_chars = [char for char in new_content if is_pua_char(char)]
    remaining_pua_counter = Counter(remaining_pua_chars)
    remaining_unique_count = len(remaining_pua_counter)
    remaining_total_count = len(remaining_pua_chars)

    # Write the output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(new_content)

    # Print statistics
    print("=" * 60)
    print("PUA Character Statistics")
    print("=" * 60)
    print(f"\nOriginal file: {input_file}")
    print(f"  - Unique PUA character types: {original_unique_count}")
    print(f"  - Total PUA character count: {original_total_count}")
    
    print(f"\nAfter replacement: {output_file}")
    print(f"  - Unique PUA character types: {remaining_unique_count}")
    print(f"  - Total PUA character count: {remaining_total_count}")
    
    print(f"\nReplaced:")
    print(f"  - Unique PUA character types: {original_unique_count - remaining_unique_count}")
    print(f"  - Total PUA characters replaced: {original_total_count - remaining_total_count}")
    print("=" * 60)

# Example usage
if __name__ == "__main__":
    translate_pua_to_standard('hoiliuk_raw.html', 'hoiliuk_new.html')
    # translate_pua_to_standard('siyen_raw.html', 'siyen_new.html')