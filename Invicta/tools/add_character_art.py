"""Add a character's pictures (Jordan's art) to the repo.

    python Invicta/tools/add_character_art.py Aurelia Aurelia.png Aurelia_Ref.png
    python Invicta/tools/add_character_art.py Avalon Avalon.png          (character sheet is optional)

What it does:
  * Saves the originals, unchanged, as game art:
        Game/Docs/art/characters/<name>/<Name>.png        square portrait
        Game/Docs/art/characters/<name>/<Name>_Ref.png    character sheet (turnaround + expressions)
    and copies them to the same path in Docs/2_Design_Docs/ (git stores the copy only once).
  * Makes the small picture Discord shows beside the character's messages:
        Invicta/web/npc/<name>.png   (512 x 512 px, published at invicta.arcanedrift.net/static/npc/<name>.png)
  * Adds the name to Invicta/web/npc/avatars.json, the list the Discord bot reads.

Needs Pillow (pip install pillow).
"""
import json
import os
import shutil
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = ("Game/Docs/art/characters", "Docs/2_Design_Docs/art/characters")
NPC = os.path.join(ROOT, "Invicta", "web", "npc")
SIZE = 512


def main(argv):
    if len(argv) not in (2, 3):
        sys.exit(__doc__)
    name, portrait = argv[0].strip(), argv[1]
    ref = argv[2] if len(argv) == 3 else None
    slug = name.lower()
    if not slug.isalpha():
        sys.exit("Use the character's one-word name, for example Aurelia.")

    for base in ART:
        folder = os.path.join(ROOT, base, slug)
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(portrait, os.path.join(folder, f"{name}.png"))
        if ref:
            shutil.copyfile(ref, os.path.join(folder, f"{name}_Ref.png"))

    os.makedirs(NPC, exist_ok=True)
    im = Image.open(portrait).convert("RGB")
    side = min(im.size)  # centre square, in case the portrait isn't square
    left, top = (im.width - side) // 2, (im.height - side) // 2
    im = im.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)
    im.save(os.path.join(NPC, f"{slug}.png"), optimize=True)

    listing = os.path.join(NPC, "avatars.json")
    names = json.load(open(listing, encoding="utf-8")) if os.path.exists(listing) else []
    if slug not in names:
        names.append(slug)
    with open(listing, "w", encoding="utf-8") as f:
        json.dump(sorted(names), f, indent=2)
        f.write("\n")
    print(f"Added {name}: art in {ART[0]}/{slug}/, Discord picture Invicta/web/npc/{slug}.png")


if __name__ == "__main__":
    main(sys.argv[1:])
