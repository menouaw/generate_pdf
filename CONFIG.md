# Configuration initiale (Windows 11) : Git Bash + MSYS2 (C:\msys64) + uv + Python 3.8 + WeasyPrint 51

## Objectif
Mettre en place un environnement **isolé et reproductible** pour un projet Python "ancien" (ex : `numpy==1.18.1`, `WeasyPrint==51`, `Jinja2==2.11.1`) en s'assurant que **les DLL natives** requises par WeasyPrint (Cairo/Pango) sont disponibles sous Windows, y compris dans un IDE (PyCharm + notebooks).

---

## 1) Installer les dépendances système via MSYS2 (Cairo / Pango)

1. Installer MSYS2 dans `C:\msys64`.
2. Ouvrir le terminal **MSYS2 MINGW64**.
3. Mettre à jour puis installer les libs nécessaires :

```bash
pacman -Syu --noconfirm
```

Fermer puis rouvrir le terminal MSYS2, puis :

```bash
pacman -S --noconfirm \
  mingw-w64-x86_64-cairo \
  mingw-w64-x86_64-pango \
  mingw-w64-x86_64-gdk-pixbuf2 \
  mingw-w64-x86_64-libffi
```

4. Vérifier la présence de Cairo :

```bash
ls /mingw64/bin/libcairo-2.dll
```

> Note : si tu utilises **UCRT64** au lieu de MINGW64, les chemins/paquets seront différents (ex : `ucrt64/bin`).

---

## 2) Configurer Git Bash pour trouver les DLL MSYS2 (indispensable pour WeasyPrint/cairocffi)

Dans **Git Bash**, ajouter MSYS2 au `PATH` (au moins pour la session en cours) :

```bash
export PATH="/c/msys64/mingw64/bin:/c/msys64/usr/bin:$PATH"
```

### Rendre permanent (recommandé)

Ajouter la ligne au `~/.bashrc` (Git Bash), puis rouvrir Git Bash :

```bash
echo 'export PATH="/c/msys64/mingw64/bin:/c/msys64/usr/bin:$PATH"' >> ~/.bashrc
```

---

## 3) Installer Python 3.8 proprement via uv

Installer un Python 3.8 géré par uv :

```bash
uv python install 3.8
uv python list
```

---

## 4) Créer un venv local au projet en Python 3.8 (avec uv)

Se placer à la racine du projet (là où est `requirements.txt`) :

```bash
cd /c/chemin/vers/ton/projet
rm -rf .venv
uv venv --python 3.8
source .venv/Scripts/activate
python -V
```

Attendu : `Python 3.8.x`

---

## 5) Installer les dépendances Python

Dans le venv activé :

```bash
uv pip install -U pip setuptools wheel
uv pip install -r requirements.txt
```

### Fix fréquent : Jinja2 2.11.x + MarkupSafe (erreur `soft_unicode`)

Si tu as `Jinja2==2.11.1`, pinner MarkupSafe :

```bash
uv pip install "markupsafe<2.1"
# Exemple stable :
uv pip install "markupsafe==2.0.1"
```

---

## 6) Vérification minimale : WeasyPrint importable (et donc Cairo visible)

Toujours dans Git Bash (PATH MSYS2 OK + venv activé) :

```bash
python -c "import weasyprint; print('WeasyPrint', weasyprint.__version__)"
```

Si tu vois `OSError: no library called "cairo-2" was found`, alors le `PATH` MSYS2 n'est pas appliqué dans **ce terminal** (ou tu n'es pas sur le bon environnement MSYS2 : `mingw64` vs `ucrt64`).

---

## 7) Optionnel : installer le projet lui-même si c'est un package Python

Si ton repo contient `setup.py` (ou `pyproject.toml`) :

```bash
uv pip install -e .
python -c "import genalog; print('import OK')"
```

---

## 8) PyCharm / Jupyter : corriger l'erreur `cairocffi` / `no library called "cairo-2"` (DLL Cairo introuvables)

En terminal Git Bash, WeasyPrint fonctionne car on injecte MSYS2 dans le `PATH`.
Dans PyCharm (kernel Jupyter), le `PATH` n'est pas forcément hérité, donc `cairocffi` ne trouve pas `libcairo-2.dll`.

### Correctif robuste (recommandé) : ajouter `sitecustomize.py` dans le venv

Créer le fichier suivant :

- `.\.venv\Lib\site-packages\sitecustomize.py`

Avec le contenu :

```python
import os

MSYS2_DLL_DIR = r"C:\msys64\mingw64\bin"  # si besoin : r"C:\msys64\ucrt64\bin"

# Force Windows à autoriser le chargement des DLL depuis ce dossier (Python 3.8+)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(MSYS2_DLL_DIR)

# Préfixe aussi le PATH, au cas où
os.environ["PATH"] = MSYS2_DLL_DIR + ";" + os.environ.get("PATH", "")
```

Ensuite :
1. Redémarrer le kernel Jupyter dans PyCharm (ou redémarrer PyCharm).
2. Vérifier dans une cellule :

```python
from cairocffi import FORMAT_ARGB32
print("Cairo OK")
```

### Diagnostic rapide si besoin

- Vérifier que la DLL existe :
    - `C:\msys64\mingw64\bin\libcairo-2.dll`
- Si la DLL est plutôt dans `ucrt64`, remplacer `mingw64` par `ucrt64` dans `sitecustomize.py`.

---

## 9) PyCharm / Notebooks : installer un kernel sans installer le méta-package `jupyter`

Certains environnements Windows échouent à installer `jupyter` (à cause de `pywinpty` et d'une toolchain manquante).
Pour exécuter des notebooks dans PyCharm, il suffit généralement d'avoir `ipykernel` + `jupyter-client` :

```bash
source .venv/Scripts/activate
uv pip install ipykernel jupyter-client
python -m ipykernel install --user --name genalog-py38 --display-name "genalog (py38)"
```

Vérifier que le kernel existe :

```bash
jupyter kernelspec list
```