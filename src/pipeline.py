import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from typing import List
import shutil

from config import GenerationConfig
from worker import _init_worker, _process_document_batch

def _iter_batches(num_documents: int, batch_size: int):
    idx = 0
    while idx < num_documents:
        yield list(range(idx, min(idx + batch_size, num_documents)))
        idx += batch_size

def _merge_worker_error_logs(run_dir: Path):
    merged = []
    for p in sorted(run_dir.glob("errors_worker_*.log")):
        try:
            merged.append(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    if merged:
        (run_dir / "errors.log").write_text("".join(merged), encoding="utf-8")
    for p in run_dir.glob("errors_worker_*.log"):
        try:
            p.unlink()
        except Exception:
            pass

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

    t0 = time.perf_counter()
    processed = 0
    errors = 0

    def args_iter():
        for batch in _iter_batches(config.num_documents, config.batch_size):
            yield (batch, content_data, str(run_dir), config_dict, config.shard_size)

    with ProcessPoolExecutor(
            max_workers=config.max_workers,
            initializer=_init_worker,
            initargs=(config.template_name, str(run_dir)),
    ) as executor:
        for (p_cnt, e_cnt) in executor.map(_process_document_batch, args_iter(), chunksize=config.chunksize):
            processed += p_cnt
            errors += e_cnt
            elapsed = time.perf_counter() - t0
            rate = processed / elapsed if elapsed > 0 else 0
            logger.info(f"Progression: {processed}/{config.num_documents} ({rate:.2f} docs/s)")

    total_time = time.perf_counter() - t0
    docs_per_second = processed / total_time if total_time > 0 else 0

    _merge_worker_error_logs(run_dir)

    report_lines = [
        f"total_documents={config.num_documents}",
        f"generated={processed}",
        f"errors={errors}",
        f"grayscale={config.grayscale}",
        f"output_format={config.output_format}",
        f"resolution={config.resolution}",
        f"batch_size={config.batch_size}",
        f"chunksize={config.chunksize}",
        f"shard_size={config.shard_size}",
        f"total_seconds={total_time:.2f}",
        f"docs_per_second={docs_per_second:.2f}",
    ]
    (run_dir / "report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    logger.info(f"Terminé: {processed} docs en {total_time:.2f}s ({docs_per_second:.2f} docs/s)")

    dps_str = f"{docs_per_second:.2f}".replace(".", "").replace(",", "")
    final_name = f"{prefix}_-_{config.num_documents}_{dps_str}"
    final_dir = output_dir / final_name
    if final_dir.exists():
        suffix = now.strftime("%S")
        final_dir = output_dir / f"{final_name}_{suffix}"
    try:
        run_dir.rename(final_dir)
    except PermissionError:
        time.sleep(0.5)
        try:
            run_dir.rename(final_dir)
        except PermissionError:
            shutil.move(str(run_dir), str(final_dir))
    return final_dir