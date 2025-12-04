import re
import sys
from argparse import ArgumentParser


def jsfuck(code):
    USE_CHAR_CODE = "USE_CHAR_CODE"
    MIN = 32
    MAX = 126

    SIMPLE = {
        'false': '![]',
        'true': '!![]',
        'undefined': '[][[]]',
        'NaN': '+[![]]',
        'Infinity': '+(+!+[]+(!+[]+[])[!+[]+!+[]+!+[]]+[+!+[]]+[+[]]+[+[]]+[+[]])'  # +"1e1000"
    }

    CONSTRUCTORS = {
        'Array': '[]',
        'Number': '(+[])',
        'String': '([]+[])',
        'Boolean': '(![])',
        'Function': '[]["fill"]',
        'RegExp': 'Function("return/"+false+"/")()'
    }

    MAPPING = {
        'a': '(false+"")[1]',
        'b': '([]["entries"]()+"")[2]',
        'c': '([]["fill"]+"")[3]',
        'd': '(undefined+"")[2]',
        'e': '(true+"")[3]',
        'f': '(false+"")[0]',
        'g': '(false+[0]+String)[20]',
        'h': '(+(101))["to"+String["name"]](21)[1]',
        'i': '([false]+undefined)[10]',
        'j': '([]["entries"]()+"")[3]',
        'k': '(+(20))["to"+String["name"]](21)',
        'l': '(false+"")[2]',
        'm': '(Number+"")[11]',
        'n': '(undefined+"")[1]',
        'o': '(true+[]["fill"])[10]',
        'p': '(+(211))["to"+String["name"]](31)[1]',
        'q': '(+(212))["to"+String["name"]](31)[1]',
        'r': '(true+"")[1]',
        's': '(false+"")[3]',
        't': '(true+"")[0]',
        'u': '(undefined+"")[0]',
        'v': '(+(31))["to"+String["name"]](32)',
        'w': '(+(32))["to"+String["name"]](33)',
        'x': '(+(101))["to"+String["name"]](34)[1]',
        'y': '(NaN+[Infinity])[10]',
        'z': '(+(35))["to"+String["name"]](36)',

        'A': '(+[]+Array)[10]',
        'B': '(+[]+Boolean)[10]',
        'C': 'Function("return escape")()(("")["italics"]())[2]',
        'D': 'Function("return escape")()([]["fill"])["slice"]("-1")',
        'E': '(RegExp+"")[12]',
        'F': '(+[]+Function)[10]',
        'G': '(false+Function("return Date")()())[30]',
        'H': USE_CHAR_CODE,
        'I': '(Infinity+"")[0]',
        'J': USE_CHAR_CODE,
        'K': USE_CHAR_CODE,
        'L': USE_CHAR_CODE,
        'M': '(true+Function("return Date")()())[30]',
        'N': '(NaN+"")[0]',
        'O': '(NaN+Function("return{}")())[11]',
        'P': USE_CHAR_CODE,
        'Q': USE_CHAR_CODE,
        'R': '(+[]+RegExp)[10]',
        'S': '(+[]+String)[10]',
        'T': '(NaN+Function("return Date")()())[30]',
        'U': '(NaN+Function("return{}")()["to"+String["name"]]["call"]())[11]',
        'V': USE_CHAR_CODE,
        'W': USE_CHAR_CODE,
        'X': USE_CHAR_CODE,
        'Y': USE_CHAR_CODE,
        'Z': USE_CHAR_CODE,

        ' ': '(NaN+[]["fill"])[11]',
        '!': USE_CHAR_CODE,
        '"': '("")["fontcolor"]()[12]',
        '#': USE_CHAR_CODE,
        '$': USE_CHAR_CODE,
        '%': 'Function("return escape")()([]["fill"])[21]',
        '&': '("")["link"](0+")[10]',
        "'": USE_CHAR_CODE,
        '(': '(undefined+[]["fill"])[22]',
        ')': '([0]+false+[]["fill"])[20]',
        '*': USE_CHAR_CODE,
        '+': '(+(+!+[]+(!+[]+[])[!+[]+!+[]+!+[]]+[+!+[]]+[+[]]+[+[]])+[])[2]',
        ',': '([]["slice"]["call"](false+"")+"")[1]',
        '-': '(+(.+[0000000001])+"")[2]',
        '.': '(+(+!+[]+[+!+[]]+(!![]+[])[!+[]+!+[]+!+[]]+[!+[]+!+[]]+[+[]])+[])[+!+[]]',
        '/': '(false+[0])["italics"]()[10]',
        ':': '(RegExp()+"")[3]',
        ';': '("")["link"](")[14]',
        '<': '("")["italics"]()[0]',
        '=': '("")["fontcolor"]()[11]',
        '>': '("")["italics"]()[2]',
        '?': '(RegExp()+"")[2]',
        '@': USE_CHAR_CODE,
        '[': '([]["entries"]()+"")[0]',
        '\\': USE_CHAR_CODE,
        ']': '([]["entries"]()+"")[22]',
        '^': USE_CHAR_CODE,
        '_': USE_CHAR_CODE,
        '`': USE_CHAR_CODE,
        '{': '(true+[]["fill"])[20]',
        '|': USE_CHAR_CODE,
        '}': '([]["fill"]+"")["slice"]("-1")',
        '~': USE_CHAR_CODE
    }

    GLOBAL = 'Function("return this")()'

    def fill_missing_chars():
        for key in list(MAPPING.keys()):
            if MAPPING[key] == USE_CHAR_CODE:
                hex_code = hex(ord(key))[2:]
                parts = []
                for c in hex_code:
                    parts.append(f'+("{c}")')
                hex_str = '"%"' + ''.join(parts)
                MAPPING[key] = f'Function("return unescape")()({hex_str})'

    def fill_missing_digits():
        for number in range(10):
            output = "+[]"
            if number > 0:
                output = "+!" + output
            for i in range(1, number):
                output = "+!+[]" + output
            if number > 1:
                output = output[1:]
            MAPPING[str(number)] = "[" + output + "]"

    def replace_map():
        def digit_replacer(match):
            x = match.group(1)
            return MAPPING[x]

        def number_replacer(match):
            y = match.group(1)
            values = list(y)
            head = int(values.pop(0))
            output = "+[]"
            if head > 0:
                output = "+!" + output
            for i in range(1, head):
                output = "+!+[]" + output
            if head > 1:
                output = output[1:]
            joined_values = '+'.join(values)
            # Use re.sub with the digit_replacer for the values part
            processed_values = re.sub(r'(\d)', digit_replacer, joined_values)
            return output + '+' + processed_values

        for i in range(MIN, MAX + 1):
            character = chr(i)
            if character not in MAPPING:
                continue
            value = MAPPING[character]
            original = value

            for key in CONSTRUCTORS:
                value = re.sub(rf'\b{key}', CONSTRUCTORS[key] + '["constructor"]', value)

            for key in SIMPLE:
                value = re.sub(re.escape(key), SIMPLE[key], value)

            value = re.sub(r'(\d\d+)', number_replacer, value)
            value = re.sub(r'\((\d)\)', digit_replacer, value)
            value = re.sub(r'\[(\d)\]', digit_replacer, value)

            value = value.replace("GLOBAL", GLOBAL)
            value = value.replace('+""', "+[]")
            value = value.replace('""', "[]+[]")

            MAPPING[character] = value

    def replace_strings():
        reg_ex = re.compile(r'[^\[\]\(\)\!\+]')
        count = MAX - MIN

        def find_missing():
            missing = {}
            for char in MAPPING:
                value = MAPPING[char]
                if reg_ex.search(value):
                    missing[char] = value
            return missing

        def mapping_replacer(match):
            return match.group(1).replace('', '+')[1:-1]

        def value_replacer(match):
            c = match.group(0)
            return missing[c] if c in missing else MAPPING[c]

        for char in MAPPING:
            MAPPING[char] = re.sub(r'"([^"]+)"', mapping_replacer, MAPPING[char])

        missing = find_missing()
        while missing:
            for char in missing:
                value = MAPPING[char]
                value = reg_ex.sub(value_replacer, value)
                MAPPING[char] = value
                missing[char] = value

            missing = find_missing()
            count -= 1
            if count == 0:
                print("Could not compile the following chars:", missing, file=sys.stderr)
                break

    def encode(input_str, wrap_with_eval=False, run_in_parent_scope=False):
        if not input_str:
            return ""

        output = []
        pattern = '|'.join(re.escape(k) for k in SIMPLE.keys()) + '|.'

        def replacement(match):
            c = match.group(0)
            if c in SIMPLE:
                return f"[{SIMPLE[c]}]+[]"
            elif c in MAPPING:
                return MAPPING[c]
            else:
                char_code = str(ord(c))
                replacement_str = (
                    f'([]+[])[{encode("constructor")}]'
                    f'[{encode("fromCharCode")}]'
                    f'({encode(char_code)})'
                )
                MAPPING[c] = replacement_str
                return replacement_str

        # Process the input string character by character
        for c in input_str:
            if c in SIMPLE:
                output.append(f"[{SIMPLE[c]}]+[]")
            elif c in MAPPING:
                output.append(MAPPING[c])
            else:
                char_code = str(ord(c))
                replacement_str = (
                    f'([]+[])[{encode("constructor")}]'
                    f'[{encode("fromCharCode")}]'
                    f'({encode(char_code)})'
                )
                MAPPING[c] = replacement_str
                output.append(replacement_str)

        encoded = '+'.join(output)

        if re.fullmatch(r'\d', input_str):
            encoded += "+[]"

        if wrap_with_eval:
            if run_in_parent_scope:
                encoded = (
                    f'[][{encode("fill")}]'
                    f'[{encode("constructor")}]'
                    f'({encode("return eval")})()'
                    f'({encoded})'
                )
            else:
                encoded = (
                    f'[][{encode("fill")}]'
                    f'[{encode("constructor")}]'
                    f'({encoded})()'
                )

        return encoded

    fill_missing_digits()
    fill_missing_chars()
    replace_map()
    replace_strings()

    js_fuck_payload = encode(code, True)
    return js_fuck_payload



def run(param):
    return jsfuck(param)


if __name__ == "__main__":
    print(run("alert(1)"))