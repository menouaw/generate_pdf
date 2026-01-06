from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

from genalog.generation.document import DocumentGenerator
from genalog.generation.content import CompositeContent, ContentType
from genalog.degradation.degrader import Degrader, ImageState


sample_text = "sample/generation/example.txt"

STYLE_COMBINATIONS = {
    "font_family": ["monospace"],
    "font_size": ["12px"],
    "text_align": ["left"],
    "language": ["en_US"],
    "hyphenate": [True],
}

HTML_TEMPLATE = "columns.html.jinja"

DEGRADATIONS = [
    ("blur", {"radius": 5}),
    (
        "bleed_through",
        {
            "src": ImageState.CURRENT_STATE,
            "background": ImageState.ORIGINAL_STATE,
            "alpha": 0.2,
            "offset_y": 9,
            "offset_x": 12,
        },
    ),
    ("morphology", {"operation": "open", "kernel_shape": (1, 1)}),
    ("pepper", {"amount": 0.05}),
    ("salt", {"amount": 0.05}),
]

DPI = 300

ts = datetime.now().strftime("%Y%m%d-%H%M%S")
out_dir = Path("output") / f"run_{ts}"
pages_dir = out_dir / "pages"
out_pdf = out_dir / f"demo_generate_{ts}.pdf"

out_dir.mkdir(parents=True, exist_ok=True)
pages_dir.mkdir(parents=True, exist_ok=True)

with open(sample_text, "r", encoding="utf-8") as f:
    text = f.read()

paragraphs = text.split("\n\n")
content = CompositeContent(paragraphs, [ContentType.PARAGRAPH] * len(paragraphs))

generator = DocumentGenerator()
generator.set_styles_to_generate(STYLE_COMBINATIONS)
doc_gen = generator.create_generator(content, [HTML_TEMPLATE])

prefix = pages_dir / "page.png"
for doc in doc_gen:
    doc.render_png(target=str(prefix), split_pages=True, resolution=DPI)

page_files = sorted(pages_dir.glob("*.png"))
if not page_files:
    raise RuntimeError("Aucune page PNG n'a été générée (split_pages).")

degrader = Degrader(DEGRADATIONS)
pdf_pages = []

for p in page_files:
    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Impossible de lire l'image: {p}")

    degraded = degrader.apply_effects(img)
    degraded = np.fliplr(degraded)

    pdf_pages.append(Image.fromarray(degraded).convert("RGB"))

pdf_pages[0].save(
    out_pdf,
    "PDF",
    resolution=float(DPI),
    save_all=True,
    append_images=pdf_pages[1:],
)

print(out_pdf.resolve())