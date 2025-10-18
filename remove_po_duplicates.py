# remove_po_duplicates.py
po_file = "locale/fr/LC_MESSAGES/django.po"

lines = open(po_file, "r", encoding="utf-8").readlines()

seen = set()
output = []
skip = False

for line in lines:
    if line.startswith('msgid '):
        if line in seen:
            skip = True
        else:
            seen.add(line)
            skip = False
    if not skip:
        output.append(line)

with open(po_file, "w", encoding="utf-8") as f:
    f.writelines(output)

print("Doublons supprimés.")
