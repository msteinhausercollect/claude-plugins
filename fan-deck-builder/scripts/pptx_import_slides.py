#!/usr/bin/env python3
"""Import native slides from one .pptx into another — editable slides, never images.

Copies each requested slide at the OPC package level: the slide XML, its rels,
all referenced media/charts, its slide layout, that layout's slide master, and
the master's theme. The imported master keeps only the layouts it actually has
relationships for, and the destination presentation gains the master + slides
at the requested positions.

Usage:
  python3 pptx_import_slides.py BASE.pptx SRC.pptx OUT.pptx  SRCNO:AFTER [SRCNO:AFTER ...]

  SRCNO  = 1-based logical slide number in SRC (order shown in PowerPoint)
  AFTER  = 1-based logical slide number in BASE to insert after (0 = front).
           Multiple imports with the same AFTER keep their argument order.

Example — pull slides 51, 29 and 61 of a source deck into a core deck:
  python3 pptx_import_slides.py Core.pptx Spain.pptx Out.pptx 51:20 29:20 61:36

Notes:
- Both decks must share the same slide size (checked; aborts otherwise).
- Speaker-notes parts are intentionally dropped.
- Stdlib only (zipfile/re) — no python-pptx needed, works on multi-GB decks.
"""
import zipfile, re, os, sys

CT_MAP = {
    'slides': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml',
    'slideLayouts': 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml',
    'slideMasters': 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml',
    'theme': 'application/vnd.openxmlformats-officedocument.theme+xml',
    'chart': 'application/vnd.openxmlformats-officedocument.drawingml.chart+xml',
}
MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'jpg': 'image/jpeg', 'gif': 'image/gif',
        'svg': 'image/svg+xml', 'emf': 'image/x-emf', 'wmf': 'image/x-wmf', 'tiff': 'image/tiff',
        'bmp': 'image/bmp', 'wdp': 'image/vnd.ms-photo', 'mp4': 'video/mp4', 'm4v': 'video/mp4',
        'mov': 'video/quicktime'}


def slide_files_in_order(z):
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    rels = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
    rid2file = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(slides/slide\d+\.xml)"', rels))
    return [rid2file[r] for r in re.findall(r'<p:sldId[^>]*r:id="(rId\d+)"', pres)]


def resolve(base_dir, target):
    out = []
    for p in (base_dir + '/' + target).split('/'):
        if p == '..':
            out.pop()
        elif p and p != '.':
            out.append(p)
    return '/'.join(out)


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    base_p, src_p, out_p = sys.argv[1:4]
    imports = [tuple(int(x) for x in a.split(':')) for a in sys.argv[4:]]

    zsrc, zbase = zipfile.ZipFile(src_p), zipfile.ZipFile(base_p)
    src_slides, base_slides = slide_files_in_order(zsrc), slide_files_in_order(zbase)
    sz = lambda z: re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', z.read('ppt/presentation.xml').decode()).groups()
    assert sz(zsrc) == sz(zbase), f'slide size mismatch: {sz(zsrc)} vs {sz(zbase)}'

    new_parts, renamed = {}, {}
    counters = {}

    def new_name_for(old):
        d, b = os.path.split(old)
        root, ext = os.path.splitext(b)
        if '/media/' in old:
            return f'{d}/imp_{b}'
        kind = ('layout' if 'slideLayouts' in d else 'master' if 'slideMasters' in d
                else 'theme' if d.endswith('theme') else 'slide' if d.endswith('slides') else 'other')
        counters[kind] = counters.get(kind, 0) + 1
        stem = {'layout': 'slideLayoutIMP', 'master': 'slideMasterIMP', 'theme': 'themeIMP',
                'slide': 'slideIMP', 'other': root + 'IMP'}[kind]
        return f'{d}/{stem}{counters[kind]}{ext}'

    def copy_part(old):
        if old in renamed:
            return renamed[old]
        new = new_name_for(old)
        renamed[old] = new
        data = zsrc.read(old)
        relpath = f'{os.path.dirname(old)}/_rels/{os.path.basename(old)}.rels'
        if relpath in zsrc.namelist():
            rels = zsrc.read(relpath).decode('utf-8')

            def fix(m):
                whole = m.group(0)
                rid = re.search(r'Id="([^"]+)"', whole).group(1)
                rtype = re.search(r'Type="([^"]+)"', whole).group(1)
                target = re.search(r'Target="([^"]+)"', whole).group(1)
                if 'notesSlide' in rtype:
                    return ''
                if target.startswith('http') or 'TargetMode="External"' in whole:
                    return whole
                tgt_new = copy_part(resolve(os.path.dirname(old), target))
                rel_new = os.path.relpath(tgt_new, os.path.dirname(new)).replace('\\', '/')
                return whole.replace(f'Target="{target}"', f'Target="{rel_new}"')

            rels2 = re.sub(r'<Relationship [^>]*/>', fix, rels)
            new_parts[f'{os.path.dirname(new)}/_rels/{os.path.basename(new)}.rels'] = rels2.encode('utf-8')
        new_parts[new] = data
        return new

    wanted = [(copy_part('ppt/' + src_slides[n - 1]), after) for n, after in imports]
    masters = sorted({v for k, v in renamed.items()
                      if 'slideMasters/' in v and v.endswith('.xml') and '_rels' not in v})

    pres = zbase.read('ppt/presentation.xml').decode('utf-8')
    prels = zbase.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
    ct = zbase.read('[Content_Types].xml').decode('utf-8')

    maxrid = max(int(r) for r in re.findall(r'Id="rId(\d+)"', prels))
    add, slide_rid, master_rid = [], {}, []
    for newp, _ in wanted:
        maxrid += 1
        slide_rid[newp] = f'rId{maxrid}'
        add.append(f'<Relationship Id="rId{maxrid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="{newp[4:]}"/>')
    for mp in masters:
        maxrid += 1
        master_rid.append(f'rId{maxrid}')
        add.append(f'<Relationship Id="rId{maxrid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="{mp[4:]}"/>')
    prels = prels.replace('</Relationships>', ''.join(add) + '</Relationships>')

    next_mid = max(int(x) for x in re.findall(r'<p:sldMasterId id="(\d+)"', pres)) + 1000
    pres = pres.replace('</p:sldMasterIdLst>',
                        ''.join(f'<p:sldMasterId id="{next_mid + i}" r:id="{r}"/>' for i, r in enumerate(master_rid))
                        + '</p:sldMasterIdLst>')

    sldids = re.findall(r'<p:sldId id="\d+" r:id="rId\d+"/>', pres)
    maxsid = max(int(x) for x in re.findall(r'<p:sldId id="(\d+)"', pres))
    inserts = {}
    for newp, after in wanted:
        maxsid += 1
        inserts.setdefault(after, []).append(f'<p:sldId id="{maxsid}" r:id="{slide_rid[newp]}"/>')
    seq = list(inserts.get(0, []))
    for idx, tag in enumerate(sldids, 1):
        seq.append(tag)
        seq.extend(inserts.get(idx, []))
    pres = pres.replace(''.join(sldids), ''.join(seq))

    add_ct = []
    for name in new_parts:
        if '_rels' in name or not name.endswith('.xml'):
            continue
        t = (CT_MAP['slides'] if '/slides/' in name else
             CT_MAP['slideLayouts'] if 'slideLayouts' in name else
             CT_MAP['slideMasters'] if 'slideMasters' in name else
             CT_MAP['theme'] if '/theme/' in name else
             CT_MAP['chart'] if '/charts/chart' in name else None)
        if t:
            add_ct.append(f'<Override PartName="/{name}" ContentType="{t}"/>')
    have = set(re.findall(r'<Default Extension="([^"]+)"', ct))
    for e in {os.path.splitext(n)[1][1:].lower() for n in new_parts if '/media/' in n} - have:
        add_ct.append(f'<Default Extension="{e}" ContentType="{MIME.get(e, "application/octet-stream")}"/>')
    ct = ct.replace('</Types>', ''.join(add_ct) + '</Types>')

    tmp = out_p + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n in zbase.namelist():
            if n == 'ppt/presentation.xml':
                zout.writestr(n, pres)
            elif n == 'ppt/_rels/presentation.xml.rels':
                zout.writestr(n, prels)
            elif n == '[Content_Types].xml':
                zout.writestr(n, ct)
            else:
                zout.writestr(n, zbase.read(n))
        for n, data in new_parts.items():
            zout.writestr(n, data)
    os.replace(tmp, out_p)

    zv = zipfile.ZipFile(out_p)
    assert zv.testzip() is None
    total = len(re.findall(r'<p:sldId ', zv.read('ppt/presentation.xml').decode()))
    print(f'OK: {out_p} — {total} slides ({len(wanted)} imported), {os.path.getsize(out_p)//1024//1024} MB')


if __name__ == '__main__':
    main()
