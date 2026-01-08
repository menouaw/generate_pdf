import logging
from dataclasses import dataclass
from typing import Optional

def setup_logging():
    logging.disable(logging.WARNING)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    for name in ["weasyprint", "weasyprint.css", "weasyprint.layout", "weasyprint.pdf", "fontTools"]:
        logging.getLogger(name).setLevel(logging.CRITICAL)
    return logger

@dataclass
class GenerationConfig:
    resolution: int = 80
    num_documents: int = 100
    batch_size: int = 50
    output_format: str = "JPEG"
    jpeg_quality: int = 70
    grayscale: bool = True
    max_workers: Optional[int] = None
    template_name: str = "columns.html.jinja"

    def to_serializable(self) -> dict:
        return {
            "resolution": self.resolution,
            "output_format": self.output_format,
            "jpeg_quality": self.jpeg_quality,
            "grayscale": self.grayscale,
        }