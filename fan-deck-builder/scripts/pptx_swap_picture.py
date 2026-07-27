#!/usr/bin/env python3
"""Swap the image behind an existing picture shape — layout, overlays, and crop frame stay intact.

Usage:
  python3 pptx_swap_picture.py DECK.pptx SLIDE_NO NEW_IMAGE [--shape NAME] [--out OUT.pptx]

  SLIDE_NO   1-based logical slide number (the number PowerPoint shows)
  NEW_IMAGE  .png / .jpg / .jpeg replacement
  --shape    name of the picture shape (as in PowerPoint's selection pane);
             default: the LARGEST picture on the slide (usually the hero photo)
  --out      output path; default: edit a copy next to the original named *_swapped.pptx

The new image is center-cropped to the frame's aspect ratio via srcRect (the
file itself is stored whole — someone can re-crop by hand later). The old image
part stays in the package (other slides may share it); only this shape repoints.
Stdlib only; safe on multi-GB decks.
"""
import re, os, struct, sys, zipfile


def img_size(path):
    data = open(path, 'rb').read(64 * 1024)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w, h = struct.unpack('>II', data[16:24])
        return w, h
    if data[:2] == b'\xff\xd8':                       # JPEG
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    sys.exit('unsupported or unreadable image: ' + path)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('deck'); ap.add_argument('slide_no', type=int); ap.add_argument('image')
    ap.add_argument('--shape'); ap.add_argument('--out')
    a = ap.parse_args()
    out = a.out or re.sub(r'\.pptx$', '_swapped.pptx', a.deck)

    z = zipfile.ZipFile(a.deck)
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    prels = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
    rid2file = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(slides/slide\d+\.xml)"', prels))
    order = re.findall(r'<p:sldId[^>]*r:id="(rId\d+)"', pres)
    slide_part = 'ppt/' + rid2file[order[a.slide_no - 1]]
    rel_part = f'{os.path.dirname(slide_part)}/_rels/{os.path.basename(slide_part)}.rels'
    xml = z.read(slide_part).decode('utf-8')
    rels = z.read(rel_part).decode('utf-8')

    pics = []
    for m in re.finditer(r'<p:pic>.*?</p:pic>', xml, re.S):
        s = m.group(0)
        name = (re.search(r'name="([^"]*)"', s) or [None, '?'])[1] if re.search(r'name="([^"]*)"', s) else '?'
        name = re.search(r'name="([^"]*)"', s).group(1)
        ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', s)
        area = int(ext.group(1)) * int(ext.group(2)) if ext else 0
        pics.append((m, name, area, ext))
    if not pics:
        sys.exit('no picture shapes on that slide')
    if a.shape:
        cand = [p for p in pics if p[1] == a.shape]
        if not cand:
            sys.exit(f'no picture named "{a.shape}" — shapes here: ' + ', '.join(p[1] for p in pics))
        target = cand[0]
    else:
        target = max(pics, key=lambda p: p[2])
    m, name, _, ext_m = target
    print(f'swapping picture "{name}" on slide {a.slide_no}')

    ext = os.path.splitext(a.image)[1].lower().lstrip('.')
    ext = 'jpeg' if ext == 'jpg' else ext
    media_name = f'ppt/media/swap_{a.slide_no}_{re.sub(r"[^A-Za-z0-9]", "_", name)[:20]}.{ext}'
    maxrid = max(int(x) for x in re.findall(r'Id="rId(\d+)"', rels))
    new_rid = f'rId{maxrid + 1}'
    rels2 = rels.replace('</Relationships>',
        f'<Relationship Id="{new_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{os.path.basename(media_name)}"/></Relationships>')

    pic_xml = m.group(0)
    pic_new = re.sub(r'r:embed="rId\d+"', f'r:embed="{new_rid}"', pic_xml, count=1)
    # center-crop to frame aspect via srcRect
    fw, fh = int(ext_m.group(1)), int(ext_m.group(2))
    iw, ih = img_size(a.image)
    frame_ar, img_ar = fw / fh, iw / ih
    if abs(frame_ar - img_ar) > 0.01:
        if img_ar > frame_ar:                      # image too wide -> crop sides
            cut = int(round((1 - frame_ar / img_ar) / 2 * 100000))
            src = f'<a:srcRect l="{cut}" r="{cut}"/>'
        else:                                      # too tall -> crop top/bottom
            cut = int(round((1 - img_ar / frame_ar) / 2 * 100000))
            src = f'<a:srcRect t="{cut}" b="{cut}"/>'
        pic_new = re.sub(r'<a:srcRect[^/]*/>', '', pic_new)
        pic_new = pic_new.replace('<a:stretch>', src + '<a:stretch>', 1) if '<a:stretch>' in pic_new \
            else pic_new.replace('</p:blipFill>', src + '<a:stretch><a:fillRect/></a:stretch></p:blipFill>', 1)
    xml2 = xml.replace(pic_xml, pic_new, 1)

    ct_extra = ''
    tmp = out + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n in z.namelist():
            if n == slide_part:
                zout.writestr(n, xml2)
            elif n == rel_part:
                zout.writestr(n, rels2)
            elif n == '[Content_Types].xml':
                ct = z.read(n).decode('utf-8')
                if f'Extension="{ext}"' not in ct:
                    mime = {'png': 'image/png', 'jpeg': 'image/jpeg'}.get(ext, 'application/octet-stream')
                    ct = ct.replace('</Types>', f'<Default Extension="{ext}" ContentType="{mime}"/></Types>')
                zout.writestr(n, ct)
            else:
                zout.writestr(n, z.read(n))
        zout.writestr(media_name, open(a.image, 'rb').read())
    os.replace(tmp, out)
    assert zipfile.ZipFile(out).testzip() is None
    print('OK ->', out)


if __name__ == '__main__':
    main()
