from genalog.generation.document import DocumentGenerator
from genalog.generation.content import CompositeContent, ContentType

from pathlib import Path
from datetime import datetime

# 1) Lire ton texte
sample_text = "sample/generation/long_example.txt"
with open(sample_text, "r", encoding="utf-8") as f:
    text = f.read()

# 2) Construire le contenu (Genalog découpe souvent par paragraphes)
paragraphs = text.split("\n\n")
content = CompositeContent(paragraphs, [ContentType.PARAGRAPH] * len(paragraphs))

# 3) Générer le document et exporter en PDF (pagination gérée ici)
HTML_TEMPLATE = "columns.html.jinja"
generator = DocumentGenerator()
doc_gen = generator.create_generator(content, [HTML_TEMPLATE])

out_dir = Path("output")
out_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
out_pdf = out_dir / f"demo_generate_without_modif_multipages_pdf_{ts}.pdf"

for doc in doc_gen:
    doc.render_pdf(target=str(out_pdf))   # -> PDF multi-pages si le contenu déborde
    print(out_pdf.resolve())