/* Shared layout + palette for the 336x480 band screen. */

export const SCREEN = { w: 336, h: 480 };

export const SPRITE = {
  w: 143,
  h: 380,
  bottom: 480,
  // horizontal anchor for each Ren'Py transform we mapped in build_story.py
  pos: {
    l: 0, c: 96, r: 193,
    cl: 24, cr: 169,
    fl: -46, l2: 48,
    r2: 210,
  },
};

export const PANEL = {
  top: 330,
  radius: 18,
  bg: 'rgba(12, 16, 28, 0.86)',
  bgSolid: '#0b0f1a',
};

export const TEXT = {
  left: 18,
  top: 356,
  width: 300,
  height: 100,
  size: 17,
  line: 24,
  color: '#eef1f6',
  dim: '#9aa4b2',
};

export const NAME = {
  top: 300,
  left: 16,
  height: 26,
  radius: 13,
  bg: 'rgba(24, 32, 52, 0.92)',
  color: '#ffd9a8',
  size: 14,
};

export const ACCENT = '#7fb3d5';
export const WARM = '#ffd9a8';

export const UI = {
  barTop: 8,
  chip: 'rgba(10, 14, 24, 0.62)',
  chipRadius: 10,
  chipSize: 11,
  chipColor: '#cfd8e3',
  hintColor: 'rgba(255, 255, 255, 0.55)',
  menuBg: 'rgba(10, 14, 22, 0.96)',
  rowH: 42,
  rowGap: 8,
  rowBg: 'rgba(255, 255, 255, 0.07)',
  rowColor: '#e6ebf2',
  rowSize: 14,
};

export function charWidth(ch, size) {
  const code = ch.codePointAt(0);
  if (code < 0x2e80) {
    // latin / digits / punctuation are roughly half width
    if (code === 0x20) return size * 0.3;
    return size * 0.56;
  }
  return size;
}

/** Wrap a line of text to `width` px, honouring explicit \n breaks. */
export function wrapText(text, width, size) {
  const lines = [];
  let line = '';
  let used = 0;
  for (const ch of text) {
    if (ch === '\n') {
      lines.push(line);
      line = '';
      used = 0;
      continue;
    }
    const w = charWidth(ch, size);
    if (used + w > width && line) {
      lines.push(line);
      line = ch;
      used = w;
    } else {
      line += ch;
      used += w;
    }
  }
  lines.push(line);
  return lines;
}

/** Split wrapped lines into pages of `maxLines` lines. */
export function paginate(text, width, size, maxLines) {
  const lines = wrapText(text, width, size);
  const pages = [];
  for (let i = 0; i < lines.length; i += maxLines) {
    pages.push(lines.slice(i, i + maxLines));
  }
  if (!pages.length) pages.push(['']);
  return pages;
}
