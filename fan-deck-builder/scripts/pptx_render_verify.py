#!/usr/bin/env python3
"""Render a .pptx via real PowerPoint (macOS) for visual QA: PDF + per-page PNGs.

Usage:
  python3 pptx_render_verify.py DECK.pptx OUTDIR [--pages 1,4,21]

Produces OUTDIR/deck.pdf and OUTDIR/page-NN.png for the requested pages
(all pages if --pages omitted; capped at 60 PNGs). LOOK at the images before
delivering a deck — this catches wrong fonts, stray comment boxes, and
wrong-country branding that structural checks cannot.

Hard-won gotchas encoded here:
- PowerPoint's automation bridge wedges (-1712) if it's already running from a
  previous heavy job -> we always force-restart it first.
- `open` returns before the file loads -> poll presentation count.
- First run needs macOS Automation permission (System Settings > Privacy &
  Security > Automation > allow the calling app to control PowerPoint) — the
  -1712 timeout is usually that dialog waiting for a click.
- Requires: pypdf (pip install pypdf); uses qlmanage (built into macOS).
"""
import os, subprocess, sys, time

APPLESCRIPT = '''
on run argv
    set inFile to POSIX file (item 1 of argv)
    set outFile to POSIX file (item 2 of argv)
    with timeout of 560 seconds
        tell application "Microsoft PowerPoint"
            launch
            delay 5
            open inFile
            repeat 150 times
                if (count of presentations) > 0 then exit repeat
                delay 2
            end repeat
            set pres to active presentation
            save pres in outFile as save as PDF
            close pres saving no
        end tell
    end timeout
    return "exported"
end run
'''


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('deck'); ap.add_argument('outdir'); ap.add_argument('--pages')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    pdf = os.path.join(os.path.abspath(a.outdir), 'deck.pdf')

    subprocess.run(['pkill', '-9', '-f', 'Microsoft PowerPoint'], capture_output=True)
    time.sleep(2)
    r = subprocess.run(['osascript', '-', os.path.abspath(a.deck), pdf],
                       input=APPLESCRIPT, text=True, capture_output=True, timeout=580)
    if r.returncode != 0 or not os.path.exists(pdf):
        sys.exit('PowerPoint export failed: ' + r.stderr.strip() +
                 '\nIf error -1712: grant Automation permission (see module docstring), then retry.')

    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(pdf)
    pages = ([int(p) for p in a.pages.split(',')] if a.pages
             else list(range(1, min(len(reader.pages), 60) + 1)))
    for p in pages:
        w = PdfWriter(); w.add_page(reader.pages[p - 1])
        one = os.path.join(a.outdir, f'page-{p:02d}.pdf')
        with open(one, 'wb') as f:
            w.write(f)
        subprocess.run(['qlmanage', '-t', '-s', '1200', '-o', a.outdir, one],
                       capture_output=True)
        png = one + '.png'
        if os.path.exists(png):
            os.replace(png, os.path.join(a.outdir, f'page-{p:02d}.png'))
        os.remove(one)
    print(f'OK: {pdf} + {len(pages)} page PNGs in {a.outdir}')


if __name__ == '__main__':
    main()
