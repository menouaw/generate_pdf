import io
import os
import logging
import img2pdf
from pathlib import Path

_worker_template = None
_worker_error_file = None

def _init_worker(template_name: str, run_dir: str):
    global _worker_template, _worker_error_file
    logging.disable(logging.WARNING)
    from genalog.generation.document import DocumentGenerator
    gen = DocumentGenerator()
    _worker_template = gen.template_env.get_template(template_name)
    pid = os.getpid()
    _worker_error_file = str(Path(run_dir) / f"errors_worker_{pid}.log")

def _render_document(doc, target_pdf: Path, config: dict):
    from PIL import Image
    image_bytes_list = []
    resolution = config["resolution"]
    output_format = config["output_format"]
    jpeg_quality = config["jpeg_quality"]
    grayscale = config["grayscale"]
    for page in doc._document.pages:
        single_page_doc = doc._document.copy([page])
        surface, width, height = single_page_doc.write_image_surface(resolution=resolution)
        img = Image.frombuffer("RGBA", (width, height), bytes(surface.get_data()), "raw", "BGRA", 0, 1)
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        if grayscale:
            output_img = bg.convert("L")
        else:
            output_img = bg
        buf = io.BytesIO()
        if output_format == "JPEG":
            if grayscale:
                output_img = output_img.convert("RGB")
            output_img.save(buf, format="JPEG", quality=jpeg_quality)
        else:
            output_img.save(buf, format="PNG", compress_level=1)
        image_bytes_list.append(buf.getvalue())
    with open(target_pdf, "wb") as f:
        f.write(img2pdf.convert(image_bytes_list))

def _process_document_batch(args):
    batch_indices, content_data, run_dir, config_dict, shard_size = args
    processed = 0
    errors = 0
    from genalog.generation.document import Document
    from genalog.generation.content import CompositeContent
    paragraphs, content_types = content_data
    content = CompositeContent(paragraphs, content_types)
    run_dir = Path(run_dir)
    for idx in batch_indices:
        try:
            shard = idx // shard_size
            shard_dir = run_dir / f"{shard:05d}"
            shard_dir.mkdir(parents=True, exist_ok=True)
            out_pdf = shard_dir / f"doc_{idx:08d}.pdf"
            if out_pdf.exists():
                processed += 1
                continue
            doc = Document(content, _worker_template)
            _render_document(doc, out_pdf, config_dict)
            processed += 1
        except Exception as e:
            errors += 1
            try:
                with open(_worker_error_file, "a", encoding="utf-8") as f:
                    f.write(f"idx={idx} error={repr(e)}\n")
            except Exception:
                pass
    return (processed, errors)