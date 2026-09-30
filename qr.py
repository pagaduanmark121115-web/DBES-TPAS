"""QR code images (with a caption under the code) and ZIP export."""
import io
import re
import zipfile


def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_qr_png(link, caption=(), box_size=10):
    """Return PNG bytes: QR code (high error correction) + caption lines below it."""
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
    from PIL import Image, ImageDraw

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=box_size, border=3)
    qr.add_data(link)
    qr.make(fit=True)
    code = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    width = max(code.width, 520)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    fonts = [_font(30), _font(24), _font(22)]
    lines = []
    for i, text in enumerate(caption):
        f = fonts[min(i, len(fonts) - 1)]
        for ln in _wrap(probe, str(text), f, width - 40):
            lines.append((ln, f))
    line_h = [int(f.size * 1.35) if hasattr(f, "size") else 30 for _, f in lines]
    height = code.height + 20 + sum(line_h) + 20

    img = Image.new("RGB", (width, height), "white")
    img.paste(code, ((width - code.width) // 2, 0))
    d = ImageDraw.Draw(img)
    y = code.height + 10
    for (ln, f), h in zip(lines, line_h):
        w = d.textlength(ln, font=f)
        d.text(((width - w) / 2, y), ln, fill="black", font=f)
        y += h
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def file_name(*parts):
    s = re.sub(r"[^A-Za-z0-9]+", "_", "_".join(p for p in parts if p)).strip("_")
    return s[:90] + ".png"


def zip_qr(items):
    """items: iterable of (filename, png_bytes) -> ZIP bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items:
            z.writestr(name, data)
    return buf.getvalue()
