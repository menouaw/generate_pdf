import os
from pathlib import Path
from config import GenerationConfig, setup_logging
from pipeline import run_pipeline

def main():
    logger = setup_logging()
    config = GenerationConfig()
    sample_text = "../explore/sample/generation/long_example.txt"
    if os.path.exists(sample_text):
        with open(sample_text, "r", encoding="utf-8") as f:
            paragraphs = [p for p in f.read().split("\n\n") if p.strip()]
    else:
        paragraphs = ["Paragraphe de test pour la génération."] * 20
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    result_dir = run_pipeline(config, paragraphs, output_dir, logger)
    print(f"\nRésultats: {result_dir.resolve()}")

if __name__ == "__main__":
    main()