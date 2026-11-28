# Character art

Jordan's pictures of the ship's digital assistants, one folder per character:

- `<Name>.png`: square portrait. A 512 px copy is the character's picture in Discord.
- `<Name>_Ref.png`: character sheet (turnaround and expressions), the reference for the game model.

To add a character, run from the repo root:

    python Invicta/tools/add_character_art.py <Name> <Name>.png <Name>_Ref.png

It saves both files here and in `Docs/2_Design_Docs/art/characters/`, and makes the Discord
picture in `Invicta/web/npc/`. Avalon's picture also becomes the bot's own picture once merged.

| Character | Role | Added |
|---|---|---|
| Avalon | Lead digital assistant, runs the whole ship | 28 Nov 2026 |
| Aurelia | City assistant, Solenne (Deck 1) | 28 Nov 2026 |
| Lyra | City assistant, Halcyon (Deck 2) | 28 Nov 2026 |
| Mira | City assistant, Meridian (Deck 3) | 28 Nov 2026 |
| Sentinel | City assistant, Bastion (Deck 4) | 28 Nov 2026 |
