import subprocess
from pathlib import Path

# === Langues du projet ===
LANGUAGES = [
    ("fr", "Français"),
    ("en", "English"),
    ("nl", "Nederlands"),
    ("es", "Español"),
]

# === Dossier contenant les templates ===
TEMPLATES_DIR = Path("templates/ngo")

def generate_po_for_page(page_name, lang_code):
    """Exécute makemessages pour une page spécifique."""
    print(f"📝 Génération du fichier {page_name}.po pour {lang_code}...")

    cmd = [
        "django-admin",
        "makemessages",
        "-l", lang_code,
        "-d", "django",  # domaine django (obligatoire)
        "-e", "html,txt",
        "--ignore", "venv/*",
        "--ignore", "env/*",
    ]

    # On se place dans le dossier de la page
    cwd = TEMPLATES_DIR / page_name

    if cwd.exists():
        subprocess.run(cmd, cwd=cwd)
        print(f"✅ Fichier {page_name}.po généré pour {lang_code}\n")
    else:
        print(f"⚠️ Dossier introuvable pour {page_name}\n")


def main():
    # Vérifie que le dossier templates/ngo existe
    if not TEMPLATES_DIR.exists():
        print("❌ Dossier 'templates/ngo' introuvable.")
        return

    # Liste des sous-dossiers dans templates/ngo
    pages = [p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir()]

    print("🌍 Début de la génération des fichiers .po...\n")

    for lang_code, lang_name in LANGUAGES:
        print(f"=== Langue : {lang_name} ({lang_code}) ===")
        for page in pages:
            generate_po_for_page(page, lang_code)

    print("🎉 Tous les fichiers .po ont été générés par page !\n")


if __name__ == "__main__":
    main()
