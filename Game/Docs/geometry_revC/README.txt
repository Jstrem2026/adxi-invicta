Luxuria Invicta - concept hull and trimmed decks, Revision C (28 Nov 2026; errata C9 and C10)
Same axes as Revision B: x km from prow tip (0) to stern (34.0); y km across beam, port negative; z km above keel.

Where it comes from
- Jordan's six-view concept sheet (28 Nov 2026): art/concept/invicta-concept-six-views.png
  (top, bottom, left, right, front and back views).
- The TOP and LEFT views were traced by hand and scaled to the canon size. The points, the scaling and the
  deck cut live in Invicta/tools/concept_hull.py; run "python Invicta/tools/concept_hull.py" to rebuild.

Hull (C9, canon: approved by Jordan 28 Nov 2026)
- hull_plan_km_revC.csv: top view. Pointed bow, wider forward flanks, armoured side pods, blunt stern with
  the four engine nozzles, joined with the canon top view so the decks keep their full width.
  21.13 mi (34.0 km) long, 7.70 mi (12.39 km) beam, as canon. Plan area 132.1 sq mi (342.2 km2).
- hull_side_profile_km_revC.csv: side view, as the art draws it: the long thin nose and the narrower engine
  section at the stern. 2.55 mi (4.1 km) keel to dorsal plating, as canon.

Decks cut back (C10, decided by Jordan 28 Nov 2026: "you can cut back the decks")
- deckN_<City>_net_km_revC.csv and _gross_km_revC.csv: the Rev B outlines, cut square across where the
  side view can no longer hold the deck with its 590 ft (180 m) armour above and below. Nothing else moves.
  Deck 1 Solenne    6.78 to 20.37 mi (10.92 to 32.78 km)   net 56.8 sq mi (147.0 km2), was 160.0
  Deck 2 Halcyon    4.52 to 20.82 mi (7.28 to 33.50 km)    net 84.7 sq mi (219.3 km2), was 230.0
  Deck 3 Meridian   2.54 to 20.82 mi (4.10 to 33.50 km)    net 102.7 sq mi (266.0 km2), was 270.0
  Deck 4 Bastion    1.17 to 20.82 mi (1.88 to 33.50 km)    net 109.8 sq mi (284.5 km2), was 285.0
  Deck 5 Aerion     1.61 to 20.82 mi (2.59 to 33.50 km)    net 116.6 sq mi (301.9 km2), was 304.1
  Deck 6 Machina    4.49 to 20.82 mi (7.23 to 33.50 km)    net 99.9 sq mi (258.8 km2), was 275.0
  Deck 7 Claustra   6.12 to 20.82 mi (9.86 to 33.50 km)    net 81.4 sq mi (210.8 km2), was 235.0
  Deck 8 Ferrum     8.35 to 18.92 mi (13.45 to 30.45 km)   net 52.6 sq mi (136.2 km2), was 190.0
  Total net city floor: 1,824.4 km2 (704.4 sq mi). Rev B: 1,949.1 km2.
- District shapes that reach past a deck end are cut with it; their areas shrink by what was cut.
- Keelway stops left outside a deck move to the first frame 1.0 km inside the new deck end (the C8 rule):
  see Invicta/data/rules.json "revC_keelway".
- Deck 5 Strike Hangars, P1 Keelway Gate: now F5 to F8. Its seven buildings in the cut moved back with the
  same shapes and rooms; 13 filler yards and gardens were removed to make room. Backups are in the project
  files (deck-trim-backup/) and in git history.

The Crown and the Bridge Level (crown_revC.json)
- Jordan, 28 Nov 2026: "at the top, needs to be the bridge ... where the front windows are" and "add another
  level (like deck 1 but smaller) on top of deck 1 for the bridge".
- The Crown sits over the windowed module of the concept's top view, 6.65 to 11.62 mi (10.7 to 18.7 km) from
  the prow, 4.97 x 3.23 mi (8 x 5.2 km), matching canon's "Crown, about 8 km long".
- The Bridge Level inside it is like Deck 1 but smaller: 1,247 ft (380 m) clear, floor 13,058 ft (3,980 m)
  on a 197 ft (60 m) service layer above Deck 1's ceiling, 120 m in from the Crown's sides,
  14.3 sq mi (37.1 km2).
- The Crown Bridge (canon 1.2 x 0.48 x 0.15 km) sits at the Bridge Level's front, behind the windows, which
  step down to the hull in three terraces as the art draws them (the steps are an assumption).
- The Crown's roof is 2.82 mi (4.54 km) above the keel. Canon gives "about 5.5 km with the Crown and stern
  fins"; the art draws the bridge low, so the fins (not designed yet) would make up the rest.

What did NOT change
- The canon files (Docs/1_Canon_Source) and Revision B stay as they were. The ship page can still show the
  old canon hull ("Canon (old)" button).
- The game geometry file (Game/Tools/InvictaGraybox/invicta_geometry.py) now puts the Strike Hangars
  Keelway stop at F7 to match (Jordan, 28 Nov 2026). Nothing else in it changed.
