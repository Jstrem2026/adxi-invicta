Luxuria Invicta - concept hull, Revision C (PROPOSED 28 Nov 2026, awaiting Jordan; errata C9)
Same axes as Revision B: x km from prow tip (0) to stern (34.0); y km across beam, port negative; z km above keel.

Where it comes from
- Jordan's six-view concept sheet (28 Nov 2026): art/concept/invicta-concept-six-views.png
  (top, bottom, left, right, front and back views).
- The TOP and LEFT views were traced by hand and scaled to the canon size. The points and the
  scaling live in Invicta/tools/concept_hull.py; run "python Invicta/tools/concept_hull.py" to rebuild.

Files
- hull_plan_km_revC.csv: top view. Pointed bow, wider forward flanks, armoured side pods, blunt stern
  with the four engine nozzles. 21.13 mi (34.0 km) long, 7.70 mi (12.39 km) beam, as canon.
  Plan area 132.1 sq mi (342.2 km2); canon 121.7 sq mi (315.3 km2).
- hull_side_profile_km_revC.csv: side view. Hull 2.55 mi (4.1 km) keel to dorsal plating, as canon,
  dorsal plating only. The raised block the sheet draws toward the stern is left out: Jordan (28 Nov 2026)
  said the raised part on top is the bridge, where the front windows are.
- crown_revC.json: the Crown on the dorsal hull, with the Crown Bridge on its front edge.
  Place (from Jordan): over the windowed module of the concept's TOP view. It runs from 6.65 mi (10.7 km)
  to 11.62 mi (18.7 km) from the prow, so 4.97 mi (8 km) long as canon says, and 3.23 mi (5.2 km) wide.
  Its rounded front holds the forward windows. The Crown Bridge (canon 1.2 x 0.48 x 0.15 km) sits at its
  front, behind those windows, looking out over the bow.
  Heights are an ASSUMPTION: the Crown rises from the dorsal plating at 2.55 mi (4.1 km) to 3.32 mi
  (5.35 km), and the Crown Bridge tops out at 3.42 mi (5.5 km), the canon height with the Crown.

What did NOT change
- Every deck, district, precinct, block, building and room stays exactly where it is.
- Each traced shape is joined with the current hull (canon top view, Rev B side profile), so the new
  hull is never smaller than the old one anywhere. The scan checks that every deck sits inside it.
- The concept art's bow and stern are sharper than the decks allow (Decks 4 and 5 run to 0.31 mi /
  0.5 km from the prow tip). Following the art exactly would cut deck space, so the bow and stern
  keep the fuller Rev B shape there.
- The canon files (Docs/1_Canon_Source) and Revision B are untouched. The ship page can still show
  the old canon hull ("Canon (old)" button).
