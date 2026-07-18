#!/usr/bin/env python3
"""
Generates the ScriptBreak app icon set.

Design: dark charcoal (#14171d) rounded-square background, an amber
(#e8a33d) diagonal clapperboard-style band across the top-left corner,
and a bold white "SB" monogram.

Run: python3 gen_icons.py
Produces (all in this directory):
  32x32.png, 128x128.png, 128x128@2x.png, icon.png (512), icon.ico, icon.icns
"""
import os
import struct
import zlib
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

BG = (20, 23, 29, 255)        # #14171d charcoal
AMBER = (232, 163, 61, 255)   # #e8a33d
AMBER_DARK = (196, 132, 40, 255)
WHITE = (240, 242, 247, 255)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def rounded_square(size):
    """Base charcoal rounded-square canvas with a subtle diagonal amber band."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = int(size * 0.22)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=BG)

    # Diagonal clapperboard-style band across the top, amber, clipped to
    # the rounded-square shape via a mask.
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=255)

    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(band)
    band_h = size * 0.30
    # Slash band from upper-left to a bit past mid-height on the right,
    # like a clapperboard clap-stick stripe.
    pts = [
        (0, size * 0.06),
        (size, size * 0.30),
        (size, size * 0.30 + band_h),
        (0, size * 0.06 + band_h),
    ]
    bdraw.polygon(pts, fill=AMBER)

    # A thin darker accent stripe under the main band for depth.
    pts2 = [
        (0, size * 0.06 + band_h),
        (size, size * 0.30 + band_h),
        (size, size * 0.30 + band_h + size * 0.035),
        (0, size * 0.06 + band_h + size * 0.035),
    ]
    bdraw.polygon(pts2, fill=AMBER_DARK)

    band.putalpha(Image.composite(band.split()[3], Image.new("L", (size, size), 0), mask))
    img = Image.alpha_composite(img, band)
    return img, mask


def draw_monogram(img, size):
    draw = ImageDraw.Draw(img)
    font_size = int(size * 0.46)
    font = ImageFont.truetype(FONT_PATH, font_size)
    text = "SB"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] + size * 0.06
    # subtle shadow for legibility over the band
    shadow_off = max(1, size // 128)
    draw.text((x + shadow_off, y + shadow_off), text, font=font, fill=(0, 0, 0, 120))
    draw.text((x, y), text, font=font, fill=WHITE)
    return img


def make_icon(size):
    img, mask = rounded_square(size)
    img = draw_monogram(img, size)
    # re-apply rounded mask to keep corners clean after text draw
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def write_png(size, path):
    icon = make_icon(size)
    icon.save(path, "PNG")
    print(f"wrote {path} ({size}x{size})")
    return icon


def write_ico(path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    imgs = [make_icon(s) for s in sizes]
    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print(f"wrote {path} (ICO, sizes={sizes})")


# --- Minimal hand-rolled ICNS writer (PNG-backed icon types) ---
# ICNS container: 8-byte header "icns" + uint32 total length, followed by
# a sequence of TLV chunks: 4-byte OSType tag + uint32 chunk length
# (including the 8-byte tag+length) + raw PNG bytes for the modern
# PNG-based icon types (ic07..ic10 etc).
ICNS_PNG_TYPES = {
    16: b"icp4",
    32: b"icp5",
    64: b"icp6",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}


def write_icns(path, sizes=(16, 32, 64, 128, 256, 512, 1024)):
    chunks = b""
    for s in sizes:
        if s not in ICNS_PNG_TYPES:
            continue
        icon = make_icon(s)
        buf_path = "/tmp/_icns_tmp.png"
        icon.save(buf_path, "PNG")
        with open(buf_path, "rb") as f:
            png_bytes = f.read()
        tag = ICNS_PNG_TYPES[s]
        chunk_len = 8 + len(png_bytes)
        chunks += tag + struct.pack(">I", chunk_len) + png_bytes
    total_len = 8 + len(chunks)
    header = b"icns" + struct.pack(">I", total_len)
    with open(path, "wb") as f:
        f.write(header)
        f.write(chunks)
    print(f"wrote {path} (ICNS, {len(chunks)} bytes of chunk data, sizes={sizes})")


if __name__ == "__main__":
    write_png(32, os.path.join(HERE, "32x32.png"))
    write_png(128, os.path.join(HERE, "128x128.png"))
    write_png(256, os.path.join(HERE, "128x128@2x.png"))
    write_png(512, os.path.join(HERE, "icon.png"))
    write_ico(os.path.join(HERE, "icon.ico"))
    write_icns(os.path.join(HERE, "icon.icns"))

    # Sanity check the icns magic bytes + non-empty.
    icns_path = os.path.join(HERE, "icon.icns")
    with open(icns_path, "rb") as f:
        magic = f.read(4)
    size_bytes = os.path.getsize(icns_path)
    assert magic == b"icns", f"bad magic: {magic!r}"
    assert size_bytes > 100, f"icns too small: {size_bytes}"
    print(f"icns OK: magic={magic!r} size={size_bytes} bytes")
