import argparse
from pathlib import Path

def cleanup_pdfs_in_run_dir(run_dir, keep_pdf=None, dry_run=False):
    run_dir = Path(run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(str(run_dir))

    pdfs = sorted(run_dir.rglob("*.pdf"))
    if not pdfs:
        return {"run_dir": str(run_dir), "deleted": 0, "kept": 0, "kept_file": None, "skipped": True}

    if keep_pdf is not None:
        keep_path = Path(keep_pdf)
        if not keep_path.is_absolute():
            keep_path = run_dir / keep_path
        keep_path = keep_path.resolve()
        if not keep_path.exists():
            raise FileNotFoundError(str(keep_path))
        if keep_path.suffix.lower() != ".pdf":
            raise ValueError("keep_pdf must be a .pdf file")
    else:
        keep_path = pdfs[0].resolve()

    deleted = 0
    kept = 0
    for p in pdfs:
        p_res = p.resolve()
        if p_res == keep_path:
            kept += 1
            continue
        if dry_run:
            deleted += 1
            continue
        p.unlink()
        deleted += 1

    return {"run_dir": str(run_dir), "deleted": deleted, "kept": kept, "kept_file": str(keep_path), "skipped": False}

def cleanup_all_output_runs(output_dir="output", keep_pdf=None, dry_run=False):
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise FileNotFoundError(str(output_dir))

    run_dirs = sorted([d for d in output_dir.iterdir() if d.is_dir()])

    results = []
    for run_dir in run_dirs:
        try:
            results.append(cleanup_pdfs_in_run_dir(run_dir, keep_pdf=keep_pdf, dry_run=dry_run))
        except Exception as e:
            results.append({"run_dir": str(run_dir), "error": str(e)})

    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--keep-pdf", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    results = cleanup_all_output_runs(
        output_dir=args.output_dir,
        keep_pdf=args.keep_pdf,
        dry_run=args.dry_run,
    )

    total_deleted = 0
    total_kept = 0
    total_dirs = 0
    total_skipped = 0
    total_errors = 0

    for r in results:
        if "error" in r:
            total_errors += 1
            print(f"ERROR run_dir={r['run_dir']} error={r['error']}")
            continue
        total_dirs += 1
        if r.get("skipped"):
            total_skipped += 1
            continue
        total_deleted += r["deleted"]
        total_kept += r["kept"]
        print(f"run_dir={r['run_dir']} kept_file={r['kept_file']} kept={r['kept']} deleted={r['deleted']}")

    print(f"run_dirs={total_dirs} skipped={total_skipped} errors={total_errors} kept_total={total_kept} deleted_total={total_deleted}")

if __name__ == "__main__":
    main()