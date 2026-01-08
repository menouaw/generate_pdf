## Guide d'utilisation

Ce projet génère des **PDF multi-pages non sélectionnables** (“scannés”) à partir d’un texte.

Le rendu se fait en **images** (PNG/JPEG) puis ces images sont **assemblées en PDF**. La génération est **parallélisée** via `ProcessPoolExecutor`.

---

## Architecture

- `main.py`

  Point d’entrée. Charge le texte, crée le pipeline, lance la génération dans `output/`.

- `config.py`

  Configuration + logging. Contient `GenerationConfig` (y compris les paramètres de performance et de sharding).

- `pipeline.py`

  Orchestration : découpe en batches, exécution parallèle, reporting, renommage final du répertoire.

  **Mise à jour** : utilisation de `executor.map` (pas de stockage de milliers/millions de futures).

- [`worker.py`](http://worker.py)

  Code exécuté dans les processus workers (init template, rendu pages→images, assemblage PDF).

  **Mise à jour** : retours IPC minimisés (le worker renvoie seulement des compteurs), erreurs écrites dans des logs worker.

- `clean_up.py`

  Nettoyage disque : supprime tous les PDF sauf 1 dans **chaque run** sous `output/`, en recherchant les PDF **récursivement** (compatible avec le sharding).


---

## Principe de génération

1. Lecture du texte et découpage en paragraphes.
2. Construction d’un `CompositeContent` (Genalog) à partir des paragraphes.
3. Dans chaque worker :
  - rendu HTML (template Jinja2) → `weasyprint.Document`
  - rendu page par page en image (Cairo surface)
  - composition sur fond blanc (suppression alpha)
  - conversion optionnelle en grayscale
  - encodage en JPEG ou PNG
  - assemblage en PDF via `img2pdf`
4. Écriture du PDF final `doc_XXXXXXXX.pdf` dans un dossier d’exécution (avec **sharding** en sous-dossiers si activé).
5. Écriture d’un rapport `report.txt`.
6. Écriture des erreurs (si besoin) dans `errors.log`.
7. Renommage du dossier final avec un indicateur de performance.

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

- `chunksize` (int)

  Paramètre passé à `executor.map`(..., chunksize=...)`.

  Augmenter `chunksize` réduit l’overhead d’ordonnancement, surtout quand il y a beaucoup de batches.

- `output_format` (str)

  `"JPEG"` ou `"PNG"`. `JPEG` est souvent plus léger et plus rapide.

- `jpeg_quality` (int)

  Qualité JPEG (0–100). Valeurs usuelles : 60–85.

- `grayscale` (bool)

  `True` pour simuler un scan N&B.

- `max_workers` (Optional[int])

  Nombre de processus. `None` laisse Python choisir.

- `template_name` (str)

  Nom du template, ex. `"columns.html.jinja"`.

- `shard_size` (int)

  Nombre de documents par sous-dossier de sortie.

  Exemple : `shard_size=1000` → `run_dir/00000/doc_00000000.pdf`, `run_dir/00001/doc_00001000.pdf`, etc.

  C’est crucial pour éviter un dossier avec des millions de fichiers.


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

## Pipeline (`run_pipeline` dans `pipeline.py`)

Le pipeline :

- crée un répertoire temporaire `output/gen_DDMM_HHMM_-_tmp`
- découpe les indices `0..num_documents-1` en batches de `batch_size`
- exécute les batches via `ProcessPoolExecutor`
- **mise à jour** : utilise `executor.map` sur un itérateur (pas de création massive de futures)
- affiche la progression et le débit (docs/s)
- écrit `report.txt`
- fusionne les logs d’erreurs worker en `errors.log` (si présents)
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
- `batch_size`
- `chunksize`
- `shard_size`
- `total_seconds`
- `docs_per_second`

---

## Worker ([`worker.py`](http://worker.py))

### Initialisation worker (`_init_worker`)

Appelée **une seule fois par process** via `initializer=` dans `ProcessPoolExecutor` :

- charge le template Jinja2 une fois : `_worker_template`
- initialise un fichier d’erreurs par worker : `errors_worker_<pid>.log`

Objectif : éviter de recharger l’environnement / templates à chaque document.

### Traitement d’un batch (`_process_document_batch`)

Entrée :

- `batch_indices` : liste d’indices à générer
- `content_data` : `(paragraphs, content_types)`
- `run_dir` : dossier de sortie
- `config_dict` : config sérialisée
- `shard_size` : taille de shard

Pour chaque index :

- calcule le shard : `idx // shard_size`
- crée le sous-dossier shard si nécessaire
- génère `doc_XXXXXXXX.pdf` dans le shard
- **mise à jour** : retourne uniquement `(processed_count, error_count)` au master
- en cas d’erreur : écrit la ligne `idx=... error=...` dans le fichier d’erreur du worker

### Rendu (page → image → bytes → PDF)

Fonction `_render_document(doc, target_pdf, config)` :

- parcourt `doc._document.pages`
- rend la page en surface Cairo : `write_image_surface(resolution=...)`
- conversion BGRA → image
- fond blanc (suppression alpha)
- grayscale optionnel
- encodage JPEG/PNG
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
  - `shard_size=1000` (ou 5000/10000 selon ton FS)
  - `batch_size=25..100`
  - `chunksize=1..4`
- plus qualitatif :
  - `resolution=150..300`
  - `output_format="PNG"` ou `JPEG` qualité 80–90

### 2) Lancer

Depuis la racine du projet :

```bash
python [main.py](http://main.py)
```

Sorties :

- `output/<run_folder>/<shard>/doc_00000000.pdf`, etc.
- `output/<run_folder>/report.txt`
- `output/<run_folder>/errors.log` (si erreurs)

---

## Utilisation : nettoyage disque (`clean_up.py`)

Objectif : dans chaque run sous `output/`, supprimer tous les `*.pdf` sauf 1.

**Mise à jour** : la recherche des PDFs est **récursive** (`rglob("*.pdf")`), compatible avec les sous-dossiers shardés.

### Exécution simple

Nettoie tous les runs `output/*/` :

```bash
python clean_[up.py](http://up.py)
```

### Mode simulation (recommandé)

Affiche ce qui serait supprimé :

```bash
python clean_[up.py](http://up.py) --dry-run
```

### Dossier output personnalisé

```bash
python clean_[up.py](http://up.py) --output-dir "chemin/vers/output"
```

### Conserver un PDF précis

Garde un PDF spécifique (chemin relatif au run ou chemin absolu) :

```bash
python clean_[up.py](http://up.py) --keep-pdf "00000/doc_00000000.pdf"
```

Si tu ne fournis pas `--keep-pdf`, le programme conserve le **premier PDF par ordre alphabétique** parmi tous les PDFs trouvés récursivement.

---

## Conseils performance (pour très gros volumes)

- Éviter le PNG si possible : privilégier `JPEG`.
- Ajuster `resolution` : levier n°1.
- Ajuster `max_workers` :
  - trop de workers peut saturer RAM/CPU
  - il vaut mieux un débit stable qu’un pic qui provoque des OOM.
- Ajuster `batch_size` et `chunksize` :
  - `batch_size` agit sur la latence et le coût d’appel côté worker
  - `chunksize` agit sur l’overhead de scheduling côté master
- Activer le sharding via `shard_size` pour éviter des millions de fichiers dans un seul dossier.
- SSD recommandé.

---

## Dépannage

- PDF vide/corrompu : vérifier `template_name` et l’installation de WeasyPrint (fonts, etc.).
- Lent / RAM élevée : baisser `resolution`, baisser `max_workers`, ajuster `batch_size`.
- Erreurs sporadiques : consulter `errors.log` dans le dossier de run.