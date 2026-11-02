r"""i0_idml_audit.py — BATCH I0, Часть B(г).

Разбор IDML (GBoH-...-v2.idml) как первоисточника:
  * инвентарь стилей абзацев/символов (имена — атрибуты, basedOn — Properties);
  * GREP/вложенные стили в стилях абзацев (AllGrepStyles/AllNestedStyles/
    AllNestedLineStyles в Properties) — проверка гипотезы об источнике
    cNoBreak и myHorizontalScaleForEmDashSpace*;
  * оформление плашек (ParagraphShading*/ParagraphBorder* — DesignNote,
    PlayNote, H1, H2, ...);
  * поток текста: рассказы, абзацы, стили, симв. стили, NoBreak, Br;
  * что сидит в потоке текста, а что только в вёрстке (якорные объекты,
    картинки, подписи);
  * сравнение текста главного рассказа со снятым с тегов текстом Tagged Text.

Только stdlib. Read-only.
Использование: python i0_idml_audit.py IDML_PATH TAGGED_TXT_PATH OUT_PATH
"""
import sys
import os
import re
import zipfile
import collections
import xml.etree.ElementTree as ET

CH = 4096  # размер блока для поиска расхождений


def style_short(ref):
    """'ParagraphStyle/main' / 'CharacterStyle/$ID/[No character style]' -> имя."""
    if not ref or ref == 'n':
        return '(нет)'
    m = re.search(r'/([^"/]+)$', ref)
    return m.group(1) if m else ref


def analyze_styles(zf):
    L = []
    src = zf.read('Resources/Styles.xml').decode('utf-8')
    root = ET.fromstring(src)
    para_styles, char_styles = {}, {}
    for el in root.iter():
        ln = el.tag.rsplit('}', 1)[-1]
        if ln in ('ParagraphStyle', 'CharacterStyle'):
            d = {'self': el.get('Self', ''), 'name': el.get('Name', ''),
                 'attrs': dict(el.attrib), 'props': {}, 'nested': []}
            for props in el:
                if props.tag.rsplit('}', 1)[-1] != 'Properties':
                    continue
                for p in props:
                    pln = p.tag.rsplit('}', 1)[-1]
                    if pln == 'BasedOn':
                        d['props']['BasedOn'] = style_short(p.text)
                    elif pln in ('AllNestedStyles', 'AllNestedLineStyles',
                                 'AllGrepStyles'):
                        for item in p:
                            rec = {}
                            for f in item:
                                rec[f.tag.rsplit('}', 1)[-1]] = \
                                    style_short(f.text) if f.text else f.get('type', '')
                            d['nested'].append((pln, rec))
                    elif pln == 'Name':
                        d['name'] = p.get('Content', d['name'])
                    else:
                        d['props'][pln] = style_short(p.text) if p.text else ''
            if ln == 'ParagraphStyle':
                para_styles[d['self']] = d
            else:
                char_styles[d['self']] = d

    L.append('=== СТИЛИ (Resources/Styles.xml) ===')
    L.append(f'ParagraphStyle: {len(para_styles)}, CharacterStyle: {len(char_styles)}')
    L.append('')
    L.append('-- Символьные стили:')
    for sid, st in char_styles.items():
        keep = {k: v for k, v in st['props'].items()
                if k in ('BasedOn', 'AppliedFont', 'FontStyle', 'PointSize',
                         'NoBreak', 'HorizontalScale')}
        L.append(f'   {st["name"]}: {keep}')
    L.append('')
    L.append('-- Стили абзацев (имя | basedOn | GREP/вложенные | плашки/рамки):')
    for sid, st in para_styles.items():
        a = st['attrs']
        deco = []
        for k, v in a.items():
            if k.startswith('ParagraphShading') or k.startswith('ParagraphBorder'):
                deco.append(f'{k}={v}')
        if st['props'].get('ParagraphShadingColor'):
            deco.append(f'ParagraphShadingColor={style_short(st["props"]["ParagraphShadingColor"])}')
        L.append(f'   [{st["name"]}] basedOn={st["props"].get("BasedOn", "(нет)")}'
                 f'  NextStyle={style_short(a.get("NextStyle", ""))}')
        if deco:
            L.append(f'      оформление: {"; ".join(deco)}')
        for kind, rec in st['nested']:
            L.append(f'      {kind}: {rec}')
    return L, para_styles, char_styles


def analyze_stories(zf):
    L = []
    stories = sorted(n for n in zf.namelist()
                     if re.fullmatch(r'Stories/Story_.*\.xml', n))
    L.append('')
    L.append('=== ПОТОК ТЕКСТА ===')
    L.append(f'рассказов (Stories): {len(stories)}')
    main_story = None
    main_chars = -1
    per_story = []
    total = {'paras': 0, 'chars': 0, 'nbr': 0, 'br': 0}
    global_ps = collections.Counter()
    global_cs = collections.Counter()
    anchored = []
    main_text = []
    for sn in stories:
        src = zf.read(sn).decode('utf-8')
        root = ET.fromstring(src)
        ps = collections.Counter()
        cs = collections.Counter()
        nbr = src.count('NoBreak="true"')
        chars = 0
        brs = 0
        text = []
        for psr in root.iter():
            ln = psr.tag.rsplit('}', 1)[-1]
            if ln == 'ParagraphStyleRange':
                ps[style_short(psr.get('AppliedParagraphStyle', ''))] += 1
            elif ln == 'CharacterStyleRange':
                cs[style_short(psr.get('AppliedCharacterStyle', ''))] += 1
                if psr.get('NoBreak') == 'true':
                    nbr += 0  # уже посчитано по строке; атрибут на этом элементе
            elif ln == 'Content' and psr.text:
                chars += len(psr.text)
                text.append(psr.text)
            elif ln == 'Br':
                brs += 1
        if '(1.0) Введение' in src and chars > main_chars:
            main_story = sn
            main_chars = chars
            main_text = text
        np_ = sum(ps.values())
        per_story.append((sn, np_, chars, nbr, brs, dict(ps)))
        total['paras'] += np_
        total['chars'] += chars
        total['nbr'] += nbr
        total['br'] += brs
        global_ps.update(ps)
        global_cs.update(cs)
        if 'AnchoredObjectSetting' in src:
            anchored.append((sn, src.count('AnchoredObjectSetting')))
    L.append(f'абзацев всего: {total["paras"]}; символов текста: {total["chars"]}; '
             f'NoBreak="true": {total["nbr"]}; <Br/> (принуд. перенос): {total["br"]}')
    L.append('')
    L.append('-- По рассказам (файл: абзацев, символов, NoBreak, Br):')
    for sn, np_, chars, nbr, brs, _ps in per_story:
        flag = '  <-- ГЛАВНЫЙ (содержит «(1.0) Введение»)' if sn == main_story else ''
        L.append(f'   {sn}: {np_} абз., {chars} симв., NoBreak={nbr}, Br={brs}{flag}')
    L.append('')
    L.append('-- Стили абзацев в потоке (все рассказы):')
    for s, c in global_ps.most_common():
        L.append(f'   {s}: {c}')
    L.append('')
    L.append('-- Символьные стили в потоке (все рассказы):')
    for s, c in global_cs.most_common():
        L.append(f'   {s}: {c}')
    L.append('')
    if anchored:
        L.append('Якорные объекты (AnchoredObjectSetting) в рассказах:')
        for sn, cnt in anchored:
            L.append(f'   {sn}: {cnt}')
    else:
        L.append('Якорных объектов (AnchoredObjectSetting) в рассказах НЕТ')
    return L, main_story, main_text, global_ps, global_cs


def analyze_links(zf):
    L = []
    L.append('')
    L.append('=== ССЫЛКИ / ГРАФИКА / ВЁРСТКА ===')
    names = zf.namelist()
    links = [n for n in names if 'Link' in n]
    L.append(f'файлы Links в пакете: {links if links else "нет"}')
    designmap = zf.read('designmap.xml').decode('utf-8')
    L.append(f'<Link в designmap.xml: {designmap.count("<Link ")}')
    spreads = sorted(n for n in names if n.startswith('Spreads/'))
    mast = sorted(n for n in names if n.startswith('MasterSpreads/'))
    L.append(f'Spreads: {len(spreads)}, MasterSpreads: {len(mast)}')
    # картинки: Rect/Image/Graphic в разворотах
    img_hits = 0
    rect_hits = 0
    for sp in spreads:
        s = zf.read(sp).decode('utf-8')
        img_hits += len(re.findall(r'<Image Self=', s))
        rect_hits += len(re.findall(r'<Rect Self=', s))
    L.append(f'<Image в разворотах: {img_hits}; <Rect (рамки-контейнеры): {rect_hits}')
    dom = zf.read('designmap.xml').decode('utf-8')
    m = re.search(r'DOMVersion="([^"]+)"', dom)
    if m:
        L.append(f'DOMVersion IDML: {m.group(1)} (21.5 = InDesign 2026; '
                 f'Tagged Text помечен Version:16.4 = InDesign 2021)')
    return L


def compare_texts(L, main_text, txt_path):
    L.append('')
    L.append('=== ТЕКСТ ГЛАВНОГО РАССКАЗА IDML ПРОТИВ TAGGED TEXT БЕЗ ТЕГОВ ===')
    raw = open(txt_path, 'rb').read().decode('utf-16-le')
    sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')
    from i0_tagged_text_audit import tokenize
    stripped = ''.join(v for k, v in tokenize(raw) if k == 'text')

    def norm(s):
        s = s.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        return re.sub(r'\s+', ' ', s).strip()

    a, b = norm(''.join(main_text)), norm(stripped)
    L.append(f'символов после нормализации: IDML {len(a)}, TXT {len(b)}; равны: {a == b}')
    if a != b:
        i = 0
        shown = 0
        while i < max(len(a), len(b)) and shown < 5:
            if a[i:i+CH] != b[i:i+CH]:
                lo, hi = i, min(i + CH, max(len(a), len(b)))
                while lo < hi:
                    mid = (lo + hi) // 2
                    if mid >= len(a) or mid >= len(b) or a[mid] != b[mid]:
                        hi = mid
                    else:
                        lo = mid + 1
                L.append(f'  первое расхождение в позиции {lo}:')
                L.append(f'    IDML: ...{a[max(0,lo-70):lo+140]!r}')
                L.append(f'    TXT : ...{b[max(0,lo-70):lo+140]!r}')
                shown += 1
                i = max(i + CH, lo + CH)
                continue
            i += CH
        nb = sum(1 for k in range(0, max(len(a), len(b)), CH)
                 if a[k:k+CH] != b[k:k+CH])
        tb = (max(len(a), len(b)) + CH - 1) // CH
        L.append(f'  несовпадающих блоков по 4К: {nb} из {tb}')
    return L


def main():
    idml_path, txt_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    zf = zipfile.ZipFile(idml_path)
    L = ['=' * 100, 'I0 / Часть B(г) — аудит IDML (первоисточник)', '=' * 100]
    L.append(f'файл: {idml_path}')

    sl, para_styles, char_styles = analyze_styles(zf)
    L += sl
    tl, main_story, main_text, gps, gcs = analyze_stories(zf)
    L += tl
    L += analyze_links(zf)
    if main_story and txt_path != '-' and os.path.exists(txt_path):
        L = compare_texts(L, main_text, txt_path)
    else:
        L.append('Сравнение с Tagged Text пропущено (txt не передан/отсутствует; '
                 'сверка с экспортом — по числам протокола i0_tagged_text_audit.out)')

    out = open(out_path, 'w', encoding='utf-8')
    out.write('\n'.join(L) + '\n')
    out.close()
    print(f'отчёт записан: {out_path}')


if __name__ == '__main__':
    main()
