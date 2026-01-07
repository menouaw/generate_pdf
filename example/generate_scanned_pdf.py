import io
import time
import img2pdf
from pathlib import Path
from datetime import datetime
from PIL import Image
from genalog.generation.document import DocumentGenerator
from genalog.generation.content import CompositeContent, ContentType

res = 80
nb = 10

def render_scanned_pdf_in_memory(doc, target_pdf, resolution=res):
    target_pdf = str(target_pdf)
    png_bytes_list = []
    for page in doc._document.pages:
        single_page_doc = doc._document.copy([page])
        surface, width, height = single_page_doc.write_image_surface(resolution=resolution)
        img = Image.frombuffer("RGBA", (width, height), bytes(surface.get_data()), "raw", "BGRA", 0, 1)
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        buf = io.BytesIO()
        bg.save(buf, format="PNG", optimize=True)
        png_bytes_list.append(buf.getvalue())
    with open(target_pdf, "wb") as f:
        f.write(img2pdf.convert(png_bytes_list))
    return target_pdf

def build_doc(content, template_name="columns.html.jinja"):
    generator = DocumentGenerator()
    doc_gen = generator.create_generator(content, [template_name])
    return next(doc_gen)

def main():
    sample_text = "sample/generation/long_example.txt"
    with open(sample_text, "r", encoding="utf-8") as f:
        text = f.read()
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    content = CompositeContent(paragraphs, [ContentType.PARAGRAPH] * len(paragraphs))

    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = out_dir / f"bench_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    for i in range(nb):
        doc = build_doc(content, template_name="columns.html.jinja")
        out_pdf = run_dir / f"scanned_multipage_{i:03d}.pdf"
        render_scanned_pdf_in_memory(doc, target_pdf=out_pdf, resolution=res)

    total_s = time.perf_counter() - t0

    results_path = run_dir / "benchmark.txt"
    results_path.write_text(
        f"count={nb}\nresolution={res}\ntotal_seconds={total_s:.6f}\nseconds_per_doc={total_s/nb:.6f}\n",
        encoding="utf-8",
    )

    print(str(run_dir.resolve()))
    print(f"total_seconds={total_s:.6f}")
    print(f"seconds_per_doc={total_s/nb:.6f}")

if __name__ == "__main__":
    main()