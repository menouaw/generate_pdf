import argparse
from pathlib import Path

def cleanup_pdfs_in_folder(folder, keep_pdf=None, dry_run=False):
    folder = Path(folder)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        return {"folder": str(folder), "deleted": 0, "kept": 0, "kept_file": None, "skipped": True}

    if keep_pdf is not None:
        keep_path = folder / keep_pdf if not Path(keep_pdf).is_absolute() else Path(keep_pdf)
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

    return {"folder": str(folder), "deleted": deleted, "kept": kept, "kept_file": str(keep_path), "skipped": False}

def cleanup_all_output_subdirs(output_dir="output", keep_pdf=None, dry_run=False, recursive=False):
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise FileNotFoundError(str(output_dir))

    folders = []
    if recursive:
        for d in output_dir.rglob("*"):
            if d.is_dir():
                folders.append(d)
    else:
        folders = [d for d in output_dir.iterdir() if d.is_dir()]

    results = []
    for folder in sorted(folders):
        try:
            results.append(cleanup_pdfs_in_folder(folder, keep_pdf=keep_pdf, dry_run=dry_run))
        except Exception as e:
            results.append({"folder": str(folder), "error": str(e)})

    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--keep-pdf", default=None, help="nom du PDF à conserver dans chaque dossier (sinon conserve le premier par ordre alphabétique)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--recursive", action="store_true", help="traite aussi les sous-dossiers à tous les niveaux (pas seulement output/*)")
    args = parser.parse_args()

    results = cleanup_all_output_subdirs(
        output_dir=args.output_dir,
        keep_pdf=args.keep_pdf,
        dry_run=args.dry_run,
        recursive=args.recursive,
    )

    total_deleted = 0
    total_kept = 0
    total_folders = 0
    total_skipped = 0
    total_errors = 0

    for r in results:
        if "error" in r:
            total_errors += 1
            print(f"ERROR folder={r['folder']} error={r['error']}")
            continue
        total_folders += 1
        if r.get("skipped"):
            total_skipped += 1
            continue
        total_deleted += r["deleted"]
        total_kept += r["kept"]
        print(f"folder={r['folder']} kept_file={r['kept_file']} kept={r['kept']} deleted={r['deleted']}")

    print(f"folders={total_folders} skipped={total_skipped} errors={total_errors} kept_total={total_kept} deleted_total={total_deleted}")

if __name__ == "__main__":
    main()