import io
import time
import img2pdf
import os
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Optional

# ====== DÉSACTIVER TOUS LES LOGS EXTERNES ======
logging.disable(logging.WARNING)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

for _logger_name in ["weasyprint", "weasyprint.css", "weasyprint.layout", "weasyprint.pdf", "fontTools"]:
    logging.getLogger(_logger_name).setLevel(logging.CRITICAL)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ====== CONFIGURATION ======
@dataclass
class GenerationConfig:
    resolution: int = 80
    num_documents: int = 10
    batch_size: int = 50
    output_format: str = "JPEG"          # "PNG" ou "JPEG"
    jpeg_quality: int = 70
    grayscale: bool = True              # True = niveaux de gris, False = couleur RGB
    max_workers: Optional[int] = None
    template_name: str = "columns.html.jinja"

    def to_serializable(self) -> dict:
        """Retourne uniquement les paramètres nécessaires au rendu (sérialisables)."""
        return {
            "resolution": self.resolution,
            "output_format": self.output_format,
            "jpeg_quality": self.jpeg_quality,
            "grayscale": self.grayscale,
        }


CONFIG = GenerationConfig()


# ====== WORKER PROCESS ======
_worker_generator = None
_worker_template = None


def _init_worker(template_name: str):
    """Initialisation unique par worker."""
    global _worker_generator, _worker_template

    # Désactiver tous les warnings dans le worker
    logging.disable(logging.WARNING)

    from genalog.generation.document import DocumentGenerator

    _worker_generator = DocumentGenerator()
    _worker_template = _worker_generator.template_env.get_template(template_name)


def _process_document_batch(args):
    """Traite un batch de documents."""
    batch_indices, content_data, run_dir, config_dict = args
    results = []

    from genalog.generation.document import Document
    from genalog.generation.content import CompositeContent, ContentType

    paragraphs, content_types = content_data
    content = CompositeContent(paragraphs, content_types)
    run_dir = Path(run_dir)

    for idx in batch_indices:
        try:
            doc = Document(content, _worker_template)
            out_pdf = run_dir / f"doc_{idx:08d}.pdf"
            _render_document(doc, out_pdf, config_dict)
            results.append((idx, str(out_pdf), None))
        except Exception as e:
            results.append((idx, None, str(e)))

    return results


def _render_document(doc, target_pdf: Path, config: dict):
    """Rendu du document en PDF avec options grayscale/couleur."""
    from PIL import Image

    image_bytes_list = []
    resolution = config["resolution"]
    output_format = config["output_format"]
    jpeg_quality = config["jpeg_quality"]
    grayscale = config["grayscale"]

    for page in doc._document.pages:
        single_page_doc = doc._document.copy([page])
        surface, width, height = single_page_doc.write_image_surface(resolution=resolution)

        # Conversion depuis le buffer Cairo (BGRA)
        img = Image.frombuffer("RGBA", (width, height), bytes(surface.get_data()), "raw", "BGRA", 0, 1)

        # Composition sur fond blanc
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])

        # Conversion grayscale si demandé
        if grayscale:
            output_img = bg.convert("L")
        else:
            output_img = bg

        # Encodage de l'image
        buf = io.BytesIO()
        if output_format == "JPEG":
            # JPEG grayscale n'est pas bien supporté par img2pdf -> reconvertir en RGB
            if grayscale:
                output_img = output_img.convert("RGB")
            output_img.save(buf, format="JPEG", quality=jpeg_quality)
        else:
            output_img.save(buf, format="PNG", compress_level=1)

        image_bytes_list.append(buf.getvalue())

    with open(target_pdf, "wb") as f:
        f.write(img2pdf.convert(image_bytes_list))


# ====== PIPELINE ======
class DocumentGenerationPipeline:
    def __init__(self, config: GenerationConfig):
        self.config = config

    def run(self, content_paragraphs: List[str], output_dir: Path) -> Path:
        from genalog.generation.content import ContentType

        # Création du répertoire de sortie
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = output_dir / f"generation_{ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        mode = "grayscale" if self.config.grayscale else "RGB"
        logger.info(f"Génération de {self.config.num_documents} documents ({mode}, {self.config.output_format})...")

        # Préparation des données
        content_types = [ContentType.PARAGRAPH] * len(content_paragraphs)
        content_data = (content_paragraphs, content_types)
        config_dict = self.config.to_serializable()

        # Découpage en batches
        all_indices = list(range(self.config.num_documents))
        batches = [
            all_indices[i:i + self.config.batch_size]
            for i in range(0, len(all_indices), self.config.batch_size)
        ]
        batch_args = [(batch, content_data, str(run_dir), config_dict) for batch in batches]

        t0 = time.perf_counter()
        processed = 0
        errors = 0

        with ProcessPoolExecutor(
                max_workers=self.config.max_workers,
                initializer=_init_worker,
                initargs=(self.config.template_name,)
        ) as executor:

            futures = {executor.submit(_process_document_batch, args): args[0] for args in batch_args}

            for future in as_completed(futures):
                for idx, path, error in future.result():
                    if error:
                        errors += 1
                    else:
                        processed += 1

                elapsed = time.perf_counter() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                logger.info(f"Progression: {processed}/{self.config.num_documents} ({rate:.2f} docs/s)")

        total_time = time.perf_counter() - t0
        docs_per_second = processed / total_time if total_time > 0 else 0

        # Rapport
        report_lines = [
            f"total_documents={self.config.num_documents}",
            f"generated={processed}",
            f"errors={errors}",
            f"grayscale={self.config.grayscale}",
            f"output_format={self.config.output_format}",
            f"resolution={self.config.resolution}",
            f"total_seconds={total_time:.2f}",
            f"docs_per_second={docs_per_second:.2f}",
        ]
        report_path = run_dir / "report.txt"
        report_path.write_text("\n".join(report_lines), encoding="utf-8")

        logger.info(f"Terminé: {processed} docs en {total_time:.2f}s ({docs_per_second:.2f} docs/s)")
        return run_dir


# ====== MAIN ======
def main():
    sample_text = "../explore/sample/generation/long_example.txt"

    if os.path.exists(sample_text):
        with open(sample_text, "r", encoding="utf-8") as f:
            paragraphs = [p for p in f.read().split("\n\n") if p.strip()]
    else:
        paragraphs = ["Paragraphe de test pour la génération."] * 20

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = DocumentGenerationPipeline(CONFIG)
    result_dir = pipeline.run(paragraphs, output_dir)
    print(f"\nRésultats: {result_dir.resolve()}")


if __name__ == "__main__":
    main()