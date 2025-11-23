#!/usr/bin/env python3
"""
Rasterize a PDF and add strong noise/blur to make OCR harder.
Default output is basename_blurred.pdf next to the input.

Dependencies:
  pip install pymupdf pillow numpy
"""

import argparse
import io
import math
import sys
import getpass  # Added for secure password input
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def perlin_like_noise(width, height, scale=8.0, octaves=4, persistence=0.5, lacunarity=2.0, seed=None):
    if seed is not None:
        np.random.seed(seed)
    noise = np.zeros((height, width), dtype=np.float32)
    frequency = scale
    amplitude = 1.0
    for _ in range(octaves):
        layer = np.random.randn(height, width).astype(np.float32)
        layer = (layer - layer.min()) / (layer.max() - layer.min() + 1e-9)
        layer_img = Image.fromarray((layer * 255).astype("uint8"))
        small_w = max(1, int(width / frequency))
        small_h = max(1, int(height / frequency))
        layer_img = layer_img.resize((small_w, small_h), resample=Image.BILINEAR)
        layer_img = layer_img.resize((width, height), resample=Image.BILINEAR)
        layer = np.asarray(layer_img).astype(np.float32) / 255.0
        noise += layer * amplitude
        amplitude *= persistence
        frequency *= lacunarity
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-9)
    return noise


def add_noise_and_artifacts(
    pil_img,
    noise_strength=0.9,
    grain_scale=6.0,
    lines=0,
    alpha=0.3,
    blur_radius=2.0,
    seed=123,
):
    w, h = pil_img.size
    arr = np.asarray(pil_img).astype(np.float32) / 255.0
    base = arr if arr.ndim == 3 else np.stack([arr] * 3, axis=2)

    smooth_noise = perlin_like_noise(w, h, scale=grain_scale, octaves=4, seed=seed)
    rng = np.random.RandomState(seed)
    speckle = rng.randn(h, w).astype(np.float32) * noise_strength
    speckle = (speckle - speckle.min()) / (speckle.max() - speckle.min() + 1e-9)

    combined = 0.6 * smooth_noise + 0.4 * speckle
    combined = (combined - combined.min()) / (combined.max() - combined.min() + 1e-9)
    overlay = np.stack([combined] * 3, axis=2)

    noisy = np.clip(base * (1.0 - alpha) + overlay * alpha, 0.0, 1.0)
    noisy_img = Image.fromarray((noisy * 255).astype("uint8")).convert("RGBA")

    if lines > 0:
        draw = ImageDraw.Draw(noisy_img)
        for _ in range(lines):
            y0 = rng.randint(int(0.1 * h), int(0.9 * h))
            amplitude = rng.randint(max(1, int(0.005 * h)), max(2, int(0.03 * h)))
            freq = rng.uniform(0.0005, 0.002)
            phase = rng.uniform(0, 2 * math.pi)
            path = []
            for x in range(0, w, 6):
                yy = int(y0 + amplitude * math.sin(2 * math.pi * freq * x + phase + rng.uniform(-0.15, 0.15)))
                path.append((x, yy))
            draw.line(path, fill=(0, 0, 0, 18), width=1)

    noisy_img = noisy_img.filter(ImageFilter.GaussianBlur(radius=float(blur_radius)))
    return noisy_img.convert("RGB")


def unique_with_suffix(path: Path, suffix: str = "_blurred") -> Path:
    base = path.stem
    candidate = path.with_name(f"{base}{suffix}.pdf")
    i = 1
    while candidate.exists():
        candidate = path.with_name(f"{base}{suffix}({i}).pdf")
        i += 1
    return candidate


def build_parser():
    prog = Path(sys.argv[0]).name
    epilog = f"""
Examples:
  {prog} input.pdf
  {prog} input.pdf --dpi 300 --noise 0.9 --alpha 0.3 --blur 2.0
"""
    ap = argparse.ArgumentParser(
        prog=prog,
        description="Make OCR harder by rasterizing pages and adding noise/blur.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )
    ap.add_argument("input", nargs="?", help="Input PDF file")
    ap.add_argument("-o", "--output", help="Output PDF path (default: basename_blurred.pdf next to input)")
    ap.add_argument("--dpi", type=int, default=300, help="Rasterization DPI (default: 300)")
    ap.add_argument("--noise", type=float, default=0.9, help="Noise strength in [0, ~1.0] (default: 0.9)")
    ap.add_argument("--alpha", type=float, default=0.3, help="Texture overlay alpha in [0,1] (default: 0.3)")
    ap.add_argument("--blur", type=float, default=2.0, help="Gaussian blur radius in pixels (default: 2.0)")
    ap.add_argument("--lines", type=int, default=0, help="Number of faint sinusoidal lines per page (default: 0)")
    ap.add_argument("--seed", type=int, default=12345, help="Random seed (default: 12345)")
    return ap


def process_pdf(input_pdf: Path, output_pdf: Path, dpi=300, noise=0.9, alpha=0.3, blur=2.0, lines=0, seed=12345, user_pw=None, owner_pw=None):
    src = fitz.open(str(input_pdf))
    out = fitz.open()

    for page_num in range(len(src)):
        page = src.load_page(page_num)
        rect = page.rect
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        noisy_img = add_noise_and_artifacts(
            img, noise_strength=noise, grain_scale=6.0, lines=lines, alpha=alpha, blur_radius=blur, seed=seed + page_num
        )
        new_page = out.new_page(width=rect.width, height=rect.height)
        buf = io.BytesIO()
        noisy_img.save(buf, format="PNG", optimize=True)
        new_page.insert_image(new_page.rect, stream=buf.getvalue())

    save_kwargs = {}
    
    # Logic: If a user password is provided, enable encryption
    if user_pw:
        save_kwargs.update(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=owner_pw,  # Master key (hardcoded in main)
            user_pw=user_pw,    # View key (typed by user)
            permissions=0,      # 0 = Disable all permissions (print/copy/mod)
        )
        
    out.save(str(output_pdf), **save_kwargs)
    src.close()
    out.close()


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stdout)
        sys.exit(0)

    args = parser.parse_args()
    in_path = Path(args.input).expanduser().resolve()
    if not in_path.exists():
        print(f"Input not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output).expanduser().resolve() if args.output else unique_with_suffix(in_path)

    # --- NEW: Ask for password interactively ---
    print(f"Processing: {in_path.name}")
    user_password = getpass.getpass("Enter password to encrypt PDF (will be required to view): ")
    
    # Hardcoded owner password as requested
    OWNER_PASSWORD = "usasklli219"

    process_pdf(
        in_path,
        out_path,
        dpi=args.dpi,
        noise=args.noise,
        alpha=args.alpha,
        blur=args.blur,
        lines=args.lines,
        seed=args.seed,
        user_pw=user_password,
        owner_pw=OWNER_PASSWORD
    )
    
    print(f"Saved: {out_path}")
    if user_password:
        print("✔ Encrypted with AES-256.")
        print("✔ Operations disabled: Printing, Copying, Modification.")
        print(f"✔ Owner Password set to: {OWNER_PASSWORD}")


if __name__ == "__main__":
    main()