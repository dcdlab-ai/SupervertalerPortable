r"""i0_break_align.py — I0, уточнение по IDML 2021: сверка типов разрывов.

IDML: ParagraphStyleRange-маркер абзаца vs внутренний <Br/> (принудительный
перенос). Tagged Text: CRLF vs одиночный LF. Вопрос: что во что превращается
при экспорте Tagged Text (гипотеза: 527 PSR + 380 внутренние Br = 907 CRLF,
25 LF — литеральные переводы строк в Content).

Использование: python i0_break_align.py IDML_2021 TXT_VERBOSE OUT_PATH
"""
import sys
import zipfile
import re
import collections
import xml.etree.ElementTree as ET

MARK = '\x02'   # конец ParagraphStyleRange (маркер абзаца IDML)
FORCED = '\x01' # <Br/> внутри абзаца
U2028 = '\x05'  # литеральный U+2028 (LINE SEPARATOR) внутри Content
CRLF = '\x03'
LF = '\x04'


def extract_idml(path):
    zf = zipfile.ZipFile(path)
    # главный рассказ: самый большой, содержащий маркер
    best, best_len, best_text = None, -1, ''
    for sn in sorted(n for n in zf.namelist()
                     if re.fullmatch(r'Stories/Story_.*\.xml', n)):
        src = zf.read(sn).decode('utf-8')
        if '(1.0) Введение' not in src:
            continue
        root = ET.fromstring(src)
        text = []
        for psr in root.iter():
            if psr.tag.rsplit('}', 1)[-1] != 'ParagraphStyleRange':
                continue
            children = list(psr)
            for ci, csr in enumerate(children):
                if csr.tag.rsplit('}', 1)[-1] != 'CharacterStyleRange':
                    continue
                for el in csr:
                    t = el.tag.rsplit('}', 1)[-1]
                    if t == 'Content' and el.text:
                        text.append(el.text)
                    elif t == 'Br':
                        is_last_csr = (ci == len(children) - 1)
                        text.append(MARK if is_last_csr else FORCED)
        joined = ''.join(text)
        if len(joined) > best_len:
            best, best_len, best_text = sn, len(joined), joined
    return best, best_text


def extract_txt(path):
    raw = open(path, 'rb').read().decode('utf-16-le')
    # тело: после заголовка (до первого <ParaStyle:)
    i = raw.find('<ParaStyle:')
    # отступ назад к началу строки
    j = raw.rfind('\r\n', 0, i)
    body = raw[j + 2:]
    # снять теги, сохранив разрывы: \<-экранирование, вложенные <> заголовка
    out = []
    k, n = 0, len(body)
    depth = 0
    while k < n:
        c = body[k]
        if c == '\\' and k + 1 < n:
            if depth == 0:
                out.append(body[k + 1])
            k += 2
            continue
        if c == '<':
            depth += 1
            k += 1
            continue
        if c == '>':
            depth -= 1
            k += 1
            continue
        if depth == 0:
            out.append(c)
        k += 1
    text = ''.join(out)
    return text.replace('\r\n', CRLF).replace('\n', LF)


def main():
    idml_path, txt_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    story, it = extract_idml(idml_path)
    tt = extract_txt(txt_path)

    L = ['=' * 100,
         'I0-2021: сверка типов разрывов IDML (PSR-маркер/внутренний Br) '
         '<-> Tagged Text (CRLF/LF)', '=' * 100,
         f'главный рассказ: {story}',
         f'IDML длина: {len(it)}, TXT длина: {len(tt)}',
         f'IDML счётчики: MARK={it.count(MARK)}, FORCED={it.count(FORCED)}, '
         f'U+2028={it.count(chr(0x2028))}, FEFF={it.count(chr(0xFEFF))}, '
         f'литеральный LF в Content={it.count(chr(10))}',
         f'TXT счётчики: CRLF={tt.count(CRLF)}, LF={tt.count(LF)}']

    # FEFF убрать; U+2028 и литеральные \n в IDML-тексте — тоже разрывы
    it2 = it.replace('\ufeff', '').replace('\n', U2028).replace('\u2028', U2028)
    tt2 = tt
    plain_i = it2.replace(MARK, '').replace(FORCED, '').replace(U2028, '')
    plain_t = tt2.replace(CRLF, '').replace(LF, '')
    L.append(f'текст без разрывов совпадает: {plain_i == plain_t} '
             f'({len(plain_i)} vs {len(plain_t)})')
    if plain_i != plain_t:
        lo, hi = 0, min(len(plain_i), len(plain_t))
        while lo < hi and plain_i[lo] == plain_t[lo]:
            lo += 1
        L.append(f'  первое расхождение на {lo}:')
        L.append(f'    IDML: {plain_i[max(0,lo-60):lo+80]!r}')
        L.append(f'    TXT : {plain_t[max(0,lo-60):lo+80]!r}')

    # выровнять последовательности разрывов по тексту между ними
    def split_breaks(text, marks):
        parts = re.split('([' + marks + '])', text)
        seq = []  # (break_type, text_before)
        cur = []
        for p in parts:
            if p in marks:
                seq.append((p, ''.join(cur)))
                cur = []
            else:
                cur.append(p)
        seq.append((None, ''.join(cur)))
        return seq

    si = split_breaks(it2, MARK + FORCED + U2028)
    st = split_breaks(tt2, CRLF + LF)
    L.append(f'разрывов в IDML: {len(si)-1}, в TXT: {len(st)-1}')
    cont = collections.Counter()
    mismatch = 0
    li = lt = 0
    while li < len(si) and lt < len(st):
        ti, tj = si[li], st[lt]
        if ti[1] == tj[1]:
            cont[(ti[0], tj[0])] += 1
            li += 1
            lt += 1
        elif len(ti[1]) < len(tj[1]):
            # IDML-кусок — префикс TXT-куска: несколько IDML-разрывов подряд?
            cont[('MANY-IDML', tj[0])] += 1
            mismatch += 1
            li += 1
        else:
            cont[(ti[0], 'MANY-TXT')] += 1
            mismatch += 1
            lt += 1
    L.append(f'несостыковок выравнивания: {mismatch}')
    L.append('контингенция (IDML-тип, TXT-тип) -> число:')
    for (a, b), c in sorted(cont.items(), key=lambda x: -x[1]):
        L.append(f'  {a!r} <-> {b!r}: {c}')

    out = open(out_path, 'w', encoding='utf-8')
    out.write('\n'.join(L) + '\n')
    out.close()
    print(f'отчёт записан: {out_path}')


if __name__ == '__main__':
    main()
