"""Generate the browser simulator bundle.

The simulator runs from file:// so it cannot use ES modules (CORS): vm.js is
rewritten into a plain script that publishes window.XBY_VM, and the story is
embedded as window.XBY_STORY. Images are loaded straight from ../src.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'common')
SIM = os.path.join(ROOT, 'sim')


def strip_module(code):
    code = re.sub(r'^import .*?$', '', code, flags=re.M)
    code = re.sub(r'^export\s+(function|const|class|let|var)', r'\1', code, flags=re.M)
    code = re.sub(r'^export\s+default\s+', 'const __default = ', code, flags=re.M)
    return code


def build_vm():
    code = strip_module(open(os.path.join(SRC, 'vm.js'), encoding='utf-8').read())
    out = ['(function () {', code, '',
           'window.XBY_VM = { createReader: createReader, slotChars: slotChars, blankState: blankState };',
           '})();']
    return '\n'.join(out)


def build_assets():
    code = strip_module(open(os.path.join(SRC, 'assets.js'), encoding='utf-8').read())
    code = code.replace("'/common/img/", "'../src/common/img/")
    out = ['(function () {', code, '',
           'window.XBY_ASSETS = { BG: BG, CG: CG, CG_WIDE: CG_WIDE, SPRITES: SPRITES, bgPath: bgPath,',
           '  cgPath: cgPath, cgThumb: cgThumb, spritePath: spritePath, hasSprite: hasSprite };',
           '})();']
    return '\n'.join(out)


def build_data():
    story = os.path.join(SRC, 'story')
    index = json.load(open(os.path.join(story, 'index.txt'), encoding='utf-8'))
    chunks = {}
    for c in index['chunks']:
        chunks[c['file']] = open(os.path.join(story, c['file'].split('/')[-1]), encoding='utf-8').read()
    doc = {'index': index, 'chunks': chunks}
    return 'window.XBY_STORY = ' + json.dumps(doc, ensure_ascii=False) + ';\n'


def main():
    os.makedirs(SIM, exist_ok=True)
    files = {
        'vm.bundle.js': build_vm(),
        'assets.bundle.js': build_assets(),
        'data.js': build_data(),
    }
    for name, text in files.items():
        with open(os.path.join(SIM, name), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('%-18s %6.1f KB' % (name, os.path.getsize(os.path.join(SIM, name)) / 1024))


if __name__ == '__main__':
    main()
