import sys
import re

def find_template_content(text, start_pattern):
    match = re.search(start_pattern, text)
    if not match:
        return None

    start_index = match.end()

    balance = 1
    i = start_index
    n = len(text)

    while i < n and balance > 0:
        char = text[i]
        if char == '<':
            balance += 1
        elif char == '>':
            balance -= 1
        i += 1

    if balance == 0:
        return text[start_index:i-1]

    return None

def split_top_level_comma(text):
    balance = 0
    split_index = -1
    for i, char in enumerate(text):
        if char == '<':
            balance += 1
        elif char == '>':
            balance -= 1
        elif char == ',' and balance == 0:
            split_index = i
            pass

    commas = []
    balance = 0
    for i, char in enumerate(text):
        if char == '<':
            balance += 1
        elif char == '>':
            balance -= 1
        elif char == ',' and balance == 0:
            commas.append(i)

    if len(commas) != 1:
        pass

    if not commas:
        return None

    if len(commas) > 1:
        pass

    idx = commas[0]
    return text[:idx], text[idx+1:]

def clean_string(s):
    s = s.replace('\n', '').replace('\r', '').strip()
    s = re.sub(r'\bT\b', 'Expr', s)
    return s

def process_file(filepath, mode):
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        if mode == 'dynamics':
            # struct CSE< ... >
            pattern = r'struct\s+CSE\s*<'
            body = find_template_content(content, pattern)
            if body:
                print(clean_string(body))
                return 0
        elif mode == 'operator':
            # struct CSE_O< ... >
            pattern = r'struct\s+CSE_O\s*<'
            body = find_template_content(content, pattern)
            if body:
                parts = split_top_level_comma(body)
                if parts:
                    op, desc = parts
                    print(f"{clean_string(op)};{clean_string(desc)}")
                    return 0

        print(f"Error: Could not parse {mode} from {filepath}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 read_cse_file.py <filepath> <type>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    mode = sys.argv[2]

    sys.exit(process_file(filepath, mode))
