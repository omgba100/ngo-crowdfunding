from pathlib import Path
import shutil

# === Définition des langues du projet ===
LANGUAGES = [
    ("fr", "Français"),
    ("en", "English"),
    ("nl", "Nederlands"),
    ("es", "Español"),
]

# === Dossier principal des fichiers de traduction ===
BASE_LOCALE_DIR = Path("locale")

def merge_language_files(lang_code):
    lang_dir = BASE_LOCALE_DIR / lang_code / "LC_MESSAGES"

    if not lang_dir.exists():
        print(f"⚠️  Aucun dossier trouvé pour la langue : {lang_code}")
        return

    main_po = lang_dir / "django.po"
    backup_po = lang_dir / "django_backup.po"

    # Sauvegarde du fichier existant
    if main_po.exists():
        shutil.copy(main_po, backup_po)
        print(f"💾 Sauvegarde créée : {backup_po.name}")

    # Fusion de tous les fichiers .po sauf django.po
    with open(main_po, "w", encoding="utf-8") as merged:
        print(f"🔄 Fusion des fichiers .po pour : {lang_code}")

        for po_file in sorted(lang_dir.glob("*.po")):
            if po_file.name != "django.po":
                merged.write(f"# === Début de {po_file.name} ===\n")
                merged.write(po_file.read_text(encoding="utf-8"))
                merged.write(f"\n# === Fin de {po_file.name} ===\n\n")

    print(f"✅ Fusion terminée pour {lang_code} → {main_po}\n")


def main():
    if not BASE_LOCALE_DIR.exists():
        print("❌ Le dossier 'locale/' est introuvable dans ce projet.")
        return

    print("🌍 Début de la fusion des fichiers de traduction...\n")

    for code, name in LANGUAGES:
        merge_language_files(code)

    print("🎉 Toutes les langues ont été fusionnées avec succès !")


if __name__ == "__main__":
    main()
