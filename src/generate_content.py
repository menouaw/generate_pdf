"""
python src/generate_content.py --out-dir ../explore/sample/generation/faker --num-files 100
"""
from __future__ import annotations

import argparse
from pathlib import Path

from faker import Faker


def _write_document(path: Path, paragraphs: list[str]) -> None:
    # Convention simple: paragraphes séparés par une ligne vide (compatible avec split("\n\n"))
    text = "\n\n".join(p.strip() for p in paragraphs if p.strip()) + "\n"
    path.write_text(text, encoding="utf-8")


def generate_faker_files(
        out_dir: Path,
        *,
        num_files: int,
        locale: str = "fr_FR",
        min_paragraphs: int = 10,
        max_paragraphs: int = 25,
        min_sentences: int = 2,
        max_sentences: int = 7,
        seed: int | None = None,
        filename_prefix: str = "faker_",
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    fake = Faker(locale)
    if seed is not None:
        Faker.seed(seed)

    for i in range(num_files):
        n_paragraphs = fake.random_int(min=min_paragraphs, max=max_paragraphs)

        paragraphs: list[str] = []
        for _ in range(n_paragraphs):
            n_sentences = fake.random_int(min=min_sentences, max=max_sentences)
            paragraphs.append(" ".join(fake.sentences(nb=n_sentences)))

        out_path = out_dir / f"{filename_prefix}{i:05d}.txt"
        _write_document(out_path, paragraphs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère des fichiers .txt via Faker (français) pour alimenter le pipeline PDF.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Dossier de sortie des .txt")
    parser.add_argument("--num-files", type=int, default=100, help="Nombre de fichiers .txt à générer")

    parser.add_argument("--locale", type=str, default="fr_FR", help="Locale Faker, ex: fr_FR")
    parser.add_argument("--seed", type=int, default=None, help="Seed pour reproductibilité")

    parser.add_argument("--min-paragraphs", type=int, default=10)
    parser.add_argument("--max-paragraphs", type=int, default=25)
    parser.add_argument("--min-sentences", type=int, default=2)
    parser.add_argument("--max-sentences", type=int, default=7)

    parser.add_argument("--prefix", type=str, default="faker_", help="Préfixe des fichiers générés")

    args = parser.parse_args()

    generate_faker_files(
        args.out_dir,
        num_files=args.num_files,
        locale=args.locale,
        min_paragraphs=args.min_paragraphs,
        max_paragraphs=args.max_paragraphs,
        min_sentences=args.min_sentences,
        max_sentences=args.max_sentences,
        seed=args.seed,
        filename_prefix=args.prefix,
    )

    print(f"OK: {args.num_files} fichiers générés dans: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()