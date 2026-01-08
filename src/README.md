## Générateur de PDFs “scannés” (Genalog + WeasyPrint) — Documentation d’utilisation

Ce projet génère des **PDF multi-pages non sélectionnables** (“scannés”) à partir d’un texte.

Le rendu se fait en **images** (PNG/JPEG) puis ces images sont **assemblées en PDF**. La génération est **parallélisée** via `ProcessPoolExecutor`.

---

## Architecture (fichiers)

- `main.py`

  Point d’entrée. Charge le texte, crée le pipeline, lance la génération dans `output/`.

- `config.py`

  Configuration et logging.

- `worker.py`

  Code exécuté dans les processus workers (init template, rendu pages→images, assemblage PDF).

- `pipeline.py`

  Orchestration : découpe en batches, exécution parallèle, reporting, renommage final du répertoire.

- `clean_up.py`

  Nettoyage disque : supprime tous les PDF sauf 1 dans chaque sous-dossier de `output/`.


---

## Principe de génération (résumé)

1. Lecture du texte et découpage en paragraphes.
2. Construction d’un `CompositeContent` (Genalog) à partir des paragraphes.
3. Dans chaque worker :
    - rendu HTML (template Jinja2) → `weasyprint.Document`
    - rendu page par page en image
    - conversion optionnelle en grayscale
    - encodage en JPEG ou PNG
    - assemblage en PDF via `img2pdf`
4. Écriture du PDF final `doc_XXXXXXXX.pdf` dans un dossier d’exécution.
5. Écriture d’un rapport `report.txt`.
6. Renommage du dossier final avec un indicateur de performance.

---

## Configuration (`GenerationConfig`)

La configuration est définie dans `config.py` via une dataclass `GenerationConfig`.

Paramètres importants :

- `resolution` (int)

  Résolution de rendu (dpi). Plus haut = meilleure qualité mais plus lent et plus lourd.

- `num_documents` (int)

  Nombre de documents à générer.

- `batch_size` (int)

  Taille des lots envoyés aux workers.

- `output_format` (str)

  `"JPEG"` ou `"PNG"`.

  `JPEG` est souvent plus léger et plus rapide.

- `jpeg_quality` (int)

  Qualité JPEG (0–100). Valeurs usuelles : 60–85.

- `grayscale` (bool)

  `True` pour simuler un scan N&B.

- `max_workers` (Optional[int])

  Nombre de processus. `None` laisse Python choisir (souvent = nombre de cœurs).

- `template_name` (str)

  Nom du template, ex. `"columns.html.jinja"`.


Notes :

- `to_serializable()` retourne seulement les paramètres sérialisables envoyés au worker :
    - `resolution`, `output_format`, `jpeg_quality`, `grayscale`.

---

## Logging

Le projet désactive les logs externes (WeasyPrint, fontTools) afin d’éviter du bruit.

- `setup_logging()` configure :
    - logs globaux en `INFO`
    - logs externes en `CRITICAL`
    - désactivation des warnings

---

## Pipeline (`DocumentGenerationPipeline` / `run_pipeline`)

Le pipeline :

- crée un répertoire temporaire `output/gen_DDMM_HHMM_-_tmp`
- découpe les indices `0..num_documents-1` en batches de `batch_size`
- soumet les batches à un `ProcessPoolExecutor`
- affiche la progression et le débit (docs/s)
- écrit `report.txt`
- renomme le dossier final en incluant un indicateur de performance :
    - `gen_DDMM_HHMM_-_<num_documents>_<docs_per_second_sans_point>`
    - ex : `gen_0701_1444_-_1000_85432`

Le rapport `report.txt` contient typiquement :

- `total_documents`
- `generated`
- `errors`
- `grayscale`
- `output_format`
- `resolution`
- `total_seconds`
- `docs_per_second`

---

## Worker (`worker.py`)

### Initialisation worker (`_init_worker`)

Appelée **une seule fois par process** via `initializer=` dans `ProcessPoolExecutor` :

- crée un `DocumentGenerator`
- charge le template Jinja2 une fois : `_worker_template`

Objectif : éviter de recharger l’environnement / templates à chaque document.

### Traitement d’un batch (`_process_document_batch`)

Entrée :

- `batch_indices` : liste d’indices à générer
- `content_data` : `(paragraphs, content_types)`
- `run_dir` : dossier de sortie
- `config_dict` : config sérialisée

Pour chaque index :

- crée `Document(content, _worker_template)`
- rend `doc._document` en images page par page
- assemble en PDF `doc_XXXXXXXX.pdf`
- retourne `(idx, path_pdf, error)`

### Rendu (page → image → bytes → PDF)

Fonction `_render_document(doc, target_pdf, config)` :

- récupère chaque page `doc._document.pages`
- crée un doc single-page : `doc._document.copy([page])`
- rend en surface Cairo `write_image_surface(resolution=...)`
- conversion BGRA → image
- fond blanc (suppression alpha)
- grayscale optionnel
- encodage en JPEG/PNG
- `img2pdf.convert(image_bytes_list)` → PDF image-only

---

## Utilisation : génération

### 1) Configurer

Dans `main.py`, modifie la config (exemples) :

- rapide / dataset massif :
    - `resolution=80`
    - `output_format="JPEG"`
    - `jpeg_quality=60..75`
    - `grayscale=True`
- plus qualitatif :
    - `resolution=150..300`
    - `output_format="PNG"` ou `JPEG` qualité 80–90

### 2) Lancer

Depuis la racine du projet :

```bash
python main.py
```

Sorties :

- `output/<run_folder>/doc_00000000.pdf`, etc.
- `output/<run_folder>/report.txt`

---

## Utilisation : nettoyage disque (`clean_up.py`)

Objectif : **dans chaque sous-dossier de `output/`**, supprimer tous les `*.pdf` sauf 1.

### Exécution simple

Nettoie tous les dossiers `output/*/` :

```bash
python clean_up.py
```

### Mode simulation (recommandé)

Affiche ce qui serait supprimé :

```bash
python clean_up.py --dry-run
```

### Dossier output personnalisé

```bash
python clean_up.py --output-dir "chemin/vers/output"
```

### Nettoyage récursif

Nettoie aussi les sous-dossiers à tous les niveaux (`output/**/`) :

```bash
python clean_up.py --recursive
```

### Conserver un PDF précis dans chaque dossier

Par exemple, garder `doc_00000000.pdf` si présent :

```bash
python clean_up.py --keep-pdf "doc_00000000.pdf"
```

---

## Conseils performance (pour très gros volumes)

- **Éviter le PNG** si possible : privilégier `JPEG` (souvent beaucoup plus léger).
- Ajuster `resolution` : c’est le levier n°1.
- Ajuster `max_workers` :
    - trop de workers peut saturer RAM / CPU et ralentir
    - tester `max_workers = (cpu_count - 1)` puis ajuster.
- Ajuster `batch_size` :
    - trop petit → overhead multiprocessing
    - trop grand → latence de progression + pics mémoire
    - valeurs usuelles : 20–200 selon taille des docs.
- Stockage :
    - SSD recommandé
    - lancer un nettoyage périodique (`clean_up.py`) si tu n’as besoin que d’un échantillon.

---

## Dépannage

- **PDF vide ou corrompu** : vérifier le template (`template_name`) et que `genalog` trouve bien ses templates.
- **Lent / RAM élevée** : baisser `resolution`, baisser `max_workers`, augmenter `batch_size` modérément.
- **Trop de logs** : vérifier que `setup_logging()` est appelé au début de `main.py` et que les loggers externes sont bien forcés en `CRITICAL`.