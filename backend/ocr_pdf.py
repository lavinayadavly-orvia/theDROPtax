"""
OCR for the scanned registers, using macOS Vision.

Nine of CDSCO's forty approval lists are image tables with no text layer.
Neither pypdf nor pdfplumber reads a pixel, so those years were logged as
blocked and left. That was giving up on an installable problem: macOS ships a
text recogniser in the Vision framework, reachable from Python through pyobjc,
with no system package and no brew.

Pages are rendered at 300 dpi with PyMuPDF and passed to
VNRecognizeTextRequest at accurate level. Recognised lines come back with a
confidence, and the confidence travels with the text — OCR misreads, and a
figure lifted from a scan should be visibly weaker evidence than one lifted
from a text layer.

Usage
-----
    python3 ocr_pdf.py <file.pdf> --pages 1-3
    python3 ocr_pdf.py <file.pdf> --out <file.txt>
"""
import os
import re
import argparse

MIN_CONFIDENCE = 0.30       # below this the line is kept but flagged
DPI = 300


def ocr_page_png(png_bytes):
    """Recognised (text, confidence) lines from one page image."""
    import Vision
    import Quartz
    from Foundation import NSData

    data = NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
    source = Quartz.CGImageSourceCreateWithData(data, None)
    if not source:
        return []
    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    if not image:
        return []

    results = []

    def handler(request, error):
        for obs in request.results() or []:
            best = obs.topCandidates_(1)
            if best and len(best):
                box = obs.boundingBox()
                # Vision's origin is bottom-left and coordinates are normalised.
                results.append({
                    "text": best[0].string(),
                    "confidence": float(best[0].confidence()),
                    "x": float(box.origin.x),
                    "y": float(box.origin.y),
                    "h": float(box.size.height),
                })

    request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(False)   # drug names are not dictionary words
    handler_obj = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    handler_obj.performRequests_error_([request], None)
    return results


def rows_from_observations(obs, y_tolerance=0.008):
    """Reassemble table rows from recognised fragments.

    Vision returns observations in its own order, which for a table is
    column-major — the whole S.No column, then the whole name column. Reading
    that as text gives 400 lines of nothing. Every observation carries a
    bounding box though, so fragments sharing a horizontal band are one row,
    ordered left to right.
    """
    rows = []
    for o in sorted(obs, key=lambda o: -o["y"]):
        placed = False
        for row in rows:
            # Same row if the vertical centres sit within a tolerance scaled to
            # the text height — tight rows in a dense table, looser in a sparse one.
            tol = max(y_tolerance, o["h"] * 0.6)
            if abs((o["y"] + o["h"] / 2) - row["centre"]) <= tol:
                row["cells"].append(o)
                row["centre"] = sum(c["y"] + c["h"] / 2 for c in row["cells"]) / len(row["cells"])
                placed = True
                break
        if not placed:
            rows.append({"centre": o["y"] + o["h"] / 2, "cells": [o]})
    out = []
    for row in rows:
        cells = sorted(row["cells"], key=lambda c: c["x"])
        out.append({
            "text": "  ".join(c["text"] for c in cells),
            "cells": [c["text"] for c in cells],
            "confidence": round(min(c["confidence"] for c in cells), 3),
        })
    return out


def ocr_pdf(path, pages=None, dpi=DPI):
    """OCR a PDF. Returns (text, stats)."""
    import fitz

    doc = fitz.open(path)
    indices = range(len(doc)) if pages is None else pages
    lines, low_confidence = [], 0
    for i in indices:
        if i >= len(doc):
            continue
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        for row in rows_from_observations(ocr_page_png(pix.tobytes("png"))):
            text = re.sub(r"\s+", " ", row["text"]).strip()
            if not text:
                continue
            if row["confidence"] < MIN_CONFIDENCE:
                low_confidence += 1
            lines.append({"page": i + 1, "text": text,
                          "cells": row["cells"], "confidence": row["confidence"]})
    doc.close()
    return lines, {"pages_read": len(list(indices)), "lines": len(lines),
                   "low_confidence_lines": low_confidence}


def parse_page_range(spec, total=None):
    if not spec:
        return None
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a) - 1, int(b)))
        elif part:
            out.append(int(part) - 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default=None, help="e.g. 1-3 or 1,4,7")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dpi", type=int, default=DPI)
    args = ap.parse_args()

    lines, stats = ocr_pdf(args.pdf, parse_page_range(args.pages), args.dpi)
    print(f"  {os.path.basename(args.pdf)}")
    print(f"  {stats['pages_read']} page(s) · {stats['lines']} line(s) · "
          f"{stats['low_confidence_lines']} below {MIN_CONFIDENCE} confidence")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(l["text"] + "\n")
        print(f"  written to {args.out}")
    else:
        for l in lines[:25]:
            flag = " ⚠" if l["confidence"] < MIN_CONFIDENCE else ""
            print(f"    p{l['page']:<3} {l['confidence']:.2f}{flag}  {l['text'][:88]}")


if __name__ == "__main__":
    main()
