# Arcane Drift — Canon Errata (Revision B)

**Version:** 0.2 · 20 Nov 2026 · Layers on top of the reference folder (`C:\Studio\AI Projects\ArcaneDrift\Invicta`), which stays untouched. Accepted rows override every older source. The game build reads only Revision B values.

Legend: ✅ decided by Jordan · ⏳ proposed, awaiting answer

## 0. Decision log

| Date | ID | Jordan's decision |
|---|---|---|
| 20 Nov 2026 | A1 | **Max is the Captain of the Invicta. He is Jordan's character.** The "Supreme Commander" title and every reference to it are removed. |
| 20 Nov 2026 | A2 | **The Captain's Chair is at the centre of the main bridge**, looking out over the other officers and the window into space. |
| 20 Nov 2026 | B1 | Everyday Lance shot = **340 kilotons**. |
| 20 Nov 2026 | C1 | **Reshape** the prow and stern so every deck fits. |
| 20 Nov 2026 | D5 | Currency = **Mark**. |
| 20 Nov 2026 | F1 | Max is **Jordan's character** (played by Jordan). |
| 20 Nov 2026 | F2 | **No simulated characters.** The 260,000 drones handle upkeep. Only the nine NPCs (for now). |
| 20 Nov 2026 | G1 | **Players elect City Councils (5 per city) and an Assembly (24 delegates, 3 per city) each season.** They set taxes and laws within the Charter and have **no power over Max's command**. |
| 20 Nov 2026 | C2 | Aerion's extra **0.9 km² is taken from the Strike Hangars** (110 → 109.1 km²). |

## 1. Command and government

| ID | Item | Revision B value | State |
|---|---|---|---|
| A1 | Captain | **Max**, played by Jordan. Highest authority aboard. Holds: command of the ship, declaration of war, sole Invicta Lance authorisation, Charter ratification, appointment of XO, officers, Deck Chiefs (with XO), Fleet Admiral. Not elected; never a player-held rank. | ✅ |
| A1 | Supreme Commander | **Removed.** Every canon line that used it now reads "Captain". Canon Q54–Q58, Q196, Q202 and Q222 (elected commander, "vote Max out") are **retired**. | ✅ |
| A1 | Top player office | **Executive Officer (XO)**, appointed by Max. Below: Chief Operations Officer and the other command officers (appointed). | ⏳ (follows from A1; confirm) |
| A1 | Player elections | **City Councils** (5 per city) and the **Assembly** (24 delegates) are elected each season. They set taxes, local budgets and laws within the Charter. Neither can override the Captain's command, war powers, the Lance, appointments or Charter ratification. No election for Captain. | ✅ G1 |
| A2 | Main bridge (Throne Deck) | One **Captain's Chair** on a raised dais at the centre. Officer stations in three stepped rings in front of and around it. A great **forward window** looks out into space over the prow. The holographic tactical sphere floats above the dais. The chair wakes for the Talisman bearer (Max) in the opening. | ✅ |
| A3 | Succession | Max › XO › Avalon › Sentinel (in declared war: Max › XO › Sentinel › Avalon). Q46 retired. | ⏳ (follows from A1) |
| A4 | Ranks | 22 player positions (all 23 minus Captain). Grades E1–E9, O1 Ensign … O6 Fleet Admiral. Squadron Leader (≥O2), Cruiser Captain (≥O4). | ⏳ |
| A6 | Council rooms | Hall of Keys (Deck 1) = Grand Council ceremonial seat. Council Chamber (Bridge L7) = secure room. Assembly meets in the Chancery. | ⏳ |
| A7 | Bodies | Captain (Max) commands · Grand Council (8 NPC Governors) administers · Assembly (elected players) legislates within the Charter; City Councils run city budgets. | ✅ (G1) |

## 2. Physics and figures

| ID | Item | Old | Revision B | State |
|---|---|---|---|---|
| B1 | Lance everyday shot | 1.4×10¹⁸ J "340 Mt" | **1.44×10¹⁵ J ≈ 340 kt** (6 TW × 240 s); surge vaults hold one shot | ✅ |
| B2 | Lance full release | "breaks worlds", 1 month | Void-conduit discharge; mechanism a labelled mystery; Captain-only; 30-day respool | ⏳ |
| B3 | Mass | 143 Gt | **530 Gt**; 557 kg/m³ interior average | ⏳ |
| B4 | Void Ore energy | "spoonful powers a deck a year" | Unchanged; flagged **Void Anomaly #1** (≈500× beyond mass-energy) | ⏳ |
| B5 | Fusion role | "main" and "backup" | Void Reactor = everyday 150 GW; Fusion = battle + hot standby | ⏳ |
| B7 | Bridge escape | 3,000 / 90 d | 3,500 / 90 d or 12,000 / 10 d | ⏳ |
| B8 | Battle heat | — | Lance draw leaves as the beam; Aegis load re-radiated; ≤1 TW to keel tanks | ⏳ |
| B9 | Height overall | 4.6 km | 5.5 km with Crown and fins | ⏳ |

## 3. Geometry

| ID | Item | Revision B | State |
|---|---|---|---|
| C1 | Hull side profile | New file `geometry_revB/hull_side_profile_km_revB.csv`. Terraced prow: dorsal line 2.05 km at the tip → 2.80 at x 0.4 → 3.25 at x 1.4 → 3.70 at x 3.4 → 4.10 at x 7.4. Ventral line 1.30 at x 0.4 → 0.86 at x 1.4 → 0.42 at x 3.4 → 0 at x 6.4. Full height to x 33.55, then a 450 m-radius stern. **Verified:** all 8 decks with 180 m dorsal/ventral and 120 m flank armor fit at every 10 m station. Top view unchanged. | ✅ |
| C1 | Deck outlines | `geometry_revB/deckN_*_revB.csv`, clipped to hull minus flank armor. Only Aerion changes (net 305.0 → 304.1 km²). Total 1,949.1 km². | ✅ |
| C2 | Aerion's 0.9 km² | Taken from the Strike Hangars (110 → 109.1 km²) | ✅ |
| C3 | Width convention | Table "W" = net width at the widest frame; add gross column | ⏳ |
| C4 | Launch shafts | 32 shafts, 60 × 40 m, F16–F28, lanes D–F and T–V; "launch towers" in Decks 1–4 | ⏳ |
| C5 | Cruisers | 2,000 × 420 × 300 m; 3 Aerion Cruiser Gates (starboard, F38–F48); Drydock Prime port door 2.2 km × 340 m | ⏳ |
| C6 | Bridge interior | Superseded by A2: the main bridge is forward-facing with a window; the overhead-dome conflict goes away. The Throne Deck becomes 30 m tall (Level 12 grows 20 → 30 m, bridge height 150 → 160 m) to fit the tactical sphere. | ⏳ |
| C7 | Plan labels on Sheets S1, S4, S7 | The plans print **The Chancery** (S1), **Command Block** (S4) and **Inner Ward** (S7) inside a neighbouring district's shape. The district areas show which shape is which (15, 35 and 20 km² / 5.8, 13.5 and 7.7 sq mi). Revision B uses the shape whose area matches. Only the labels move; no areas or boundaries change. Found by the Invicta Atlas scan, 26 Nov 2026. | ⏳ |

## 4. Cities, systems, naming

| ID | Item | Revision B | State |
|---|---|---|---|
| D1 | Height limit | 300 m; landmarks ≤ 360 m, one per city | ⏳ |
| D2 | Build state | Shell, streets, transit and landmarks built; district interiors sealed until opened | ⏳ |
| D3 | Verdance weather | "Low weather" (mist, rain, wind); Mother Tree pruned at 300 m | ⏳ |
| D4 | Drone classes | Worker 120k · Maintenance 60k · Emergency 20k · Defensive 40k · Offensive 20k | ⏳ |
| D5 | Currency | **Mark (₥)** | ✅ |
| D6 | Claustra landmark | The Sealed Vault | ⏳ |
| D7 | Directions | Bow Lock / Stern Lock; Starboard Gate | ⏳ |
| D8 | Renames | Lyceum; Cybernetics Works; Works Quay; Lumen Dome | ⏳ |
| D11 | Pod stops | One per 500 × 500 m block pair | ⏳ |

## 5. Lore

| ID | Item | Revision B | State |
|---|---|---|---|
| E1 | Age of the Talisman | Power primordial; Eliam bound for centuries | ⏳ |
| E2 | Natalia ↔ Black Veil | History is the Mia tragedy; no romantic/familial/rival bond | ⏳ |
| E3 | Immortality | Consciousness immortal; bodies replaced | ⏳ |

## 6. Game-design rulings

| ID | Ruling | State |
|---|---|---|
| F1 | **Max is Jordan's character.** Jordan plays Max live (Captain's authority in-game). Max also appears in authored cinematics, performed by an actor/mocap when Jordan isn't the one on stage. | ✅ |
| F2 | **No simulated people.** Population = players + the nine NPCs. The 260,000 drones are the visible "life" of the ship (cleaning, building, hauling, farming, security). The canon population figures (1.82 M) are *capacity*, filled only by players. | ✅ |
| F3 | Jettison = ejection off-ship + loss of citizenship/rank/housing + timed ban; no permadeath unless opt-in | ⏳ |
| F4 | Invicta hub + Drift Network (1 home + 4 frontier systems) | ⏳ |
| F5 | Aboard: consensual PvP only; frontier High / Low / Void | ⏳ |
| F6 | 1 ship day = 3 real hours; season = 4 real months | ⏳ |
| F7 | Game is source of truth for ranks; Discord mirrored by bot | ⏳ |
| F8 | PC first; M / PEGI 18; soft-currency casino | ⏳ |

## 7. New questions raised by the decisions

| ID | Question | Recommendation |
|---|---|---|
| **G1** ✅ | With Max as permanent Captain, should players still elect anything? | **Decided 20 Nov: yes.** Recommended was: City Councils + Assembly (civil laws, taxes within the Charter). It keeps the "player-run" pillar without touching Max's command. |
| **G2** | When Jordan is offline, who acts for the Captain? | The XO (a player Max appoints) handles routine orders; Lance and war stay Max-only. Avalon runs the ship (canon). |
| **G3** | Who opens empty districts and fills empty shops without Settlers? | Players and drones. Districts open only as fast as players move in; drone crews keep sealed districts maintained and lit. Shops are player-run or NPC/drone-run kiosks (vending, automated stores). |
| **G4** | Does "Only the NPCs for now" leave room for simulated people later? | Keep the technology option open (no design depends on it). Revisit after Early Access. |
