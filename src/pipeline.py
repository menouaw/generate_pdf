import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

from config import GenerationConfig
from worker import _init_worker, _process_document_batch

def run_pipeline(config: GenerationConfig, content_paragraphs: List[str], output_dir: Path, logger):
    from genalog.generation.content import ContentType
    now = datetime.now()
    prefix = now.strftime("gen_%d%m_%H%M")
    run_dir = output_dir / f"{prefix}_-_tmp"
    run_dir.mkdir(parents=True, exist_ok=True)
    mode = "grayscale" if config.grayscale else "RGB"
    logger.info(f"Génération de {config.num_documents} documents ({mode}, {config.output_format})...")
    content_types = [ContentType.PARAGRAPH] * len(content_paragraphs)
    content_data = (content_paragraphs, content_types)
    config_dict = config.to_serializable()
    all_indices = list(range(config.num_documents))
    batches = [all_indices[i : i + config.batch_size] for i in range(0, len(all_indices), config.batch_size)]
    batch_args = [(batch, content_data, str(run_dir), config_dict) for batch in batches]
    t0 = time.perf_counter()
    processed = 0
    errors = 0
    with ProcessPoolExecutor(
            max_workers=config.max_workers,
            initializer=_init_worker,
            initargs=(config.template_name,),
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
            logger.info(f"Progression: {processed}/{config.num_documents} ({rate:.2f} docs/s)")
    total_time = time.perf_counter() - t0
    docs_per_second = processed / total_time if total_time > 0 else 0
    report_lines = [
        f"total_documents={config.num_documents}",
        f"generated={processed}",
        f"errors={errors}",
        f"grayscale={config.grayscale}",
        f"output_format={config.output_format}",
        f"resolution={config.resolution}",
        f"total_seconds={total_time:.2f}",
        f"docs_per_second={docs_per_second:.2f}",
    ]
    report_path = run_dir / "report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    logger.info(f"Terminé: {processed} docs en {total_time:.2f}s ({docs_per_second:.2f} docs/s)")
    dps_str = f"{docs_per_second:.2f}".replace(".", "").replace(",", "")
    final_name = f"{prefix}_-_{config.num_documents}_{dps_str}"
    final_dir = output_dir / final_name
    if final_dir.exists():
        suffix = now.strftime("%S")
        final_dir = output_dir / f"{final_name}_{suffix}"
    run_dir.rename(final_dir)
    return final_dir