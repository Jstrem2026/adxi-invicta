# Port of Arrivals: city planner check

Made by `Invicta/tools/city_planner.py` on 2026-11-28 from the program in `Invicta/data/city_programs.json`. It checks the district against what it is for and lists what is missing. Items marked **proposed** are the planner's suggestions; nothing already designed was moved or removed.

**What this district is for** (Jordan, 28 Nov 2026): The main way in and out of the whole ship. People arrive and leave here, whether military, commercial or community, so the outer hull needs many doors, big and small, and the port needs high security.

## 1. Doors in the hull

| Kind of door | Used by | Doors | Widths | Opened by | Check |
|---|---|---|---|---|---|
| Passenger shuttle gates | commercial | 17 | 131 ft (40 m), see note | Gate Operations | ✅ |
| Ship berths (civilian and private ships) | commercial | 28 | 262 ft (80 m), 367 ft (112 m), 919 ft (280 m) | Harbourmaster, Stern Harbourmaster | ✅ |
| Yard lock (ships to the repair yards) | commercial | 1 | 1,640 ft (500 m) | Harbourmaster, Stern Harbourmaster | ✅ |
| Small craft locks (skiffs and private runabouts) | community | 1 | 131 ft (40 m) | Harbourmaster, Stern Harbourmaster | ✅ |
| Guard and government berths (security, military and official craft) | military | 2 | 262 ft (80 m) | Port Guard Station | ✅ |
| Crew airlocks (small walk-through doors for crews, inspectors and suited work) | crew | 20 | 6 ft (1.8 m) | Port Security Command | ✅ |
| Freight gate (cargo ships) | commercial | 3 | 919 ft (280 m) | Harbourmaster, Stern Harbourmaster | ✅ |

Pressure zones: the hull front has 20 zones (one per 1,640 ft (500 m) frame). 20 of them have a crew airlock.

- **Guard and government berths (security, military and official craft):** Jordan: doors for military as well as commercial and community traffic. The big warships use the Cruiser Docks; the Port needs its own berths for patrol cutters, military transports and official arrivals, one at each end of the hull front.
- **Crew airlocks (small walk-through doors for crews, inspectors and suited work):** Every 1,640 ft (500 m) frame of hull is its own sealable pressure zone (Ship Reference 5), so each needs a small door that does not need a ship-sized door to open.
- **Freight gate (cargo ships):** Jordan, 28 Nov 2026: a freight gate of its own at the Port's bow end (F34 to F36), in front of Freight, with cargo teleport pads to Deck 8.

## 2. Help within reach of every door

| Service | Must be within | Doors out of reach | Furthest |
|---|---|---|---|
| Fire and rescue | 0.99 mi (1.60 km) | ✅ 0 of 52 | - |
| Police and port security | 0.99 mi (1.60 km) | ✅ 0 of 52 | - |
| Medical | 1.55 mi (2.50 km) | ✅ 0 of 52 | - |
| Border clearance (passport, customs and health checks) | 1.24 mi (2.00 km) | ✅ 0 of 52 | - |

- **Fire and rescue:** Airport fire rules: crash rescue reaches any point of a runway in 3 minutes, about 1 mile (1.6 km).
- **Police and port security:** Every hull door is a way into the ship; a police post within about a mile can reach it in minutes.
- **Medical:** Injured crew or sick arrivals reach a clinic within about 1.5 miles (2.5 km).
- **Border clearance (passport, customs and health checks):** Everyone who comes through a hull door is checked before they reach the public side of the port. Each door needs a clearance point close by, so no one walks a long way unchecked.

Fire, police and medical buildings just over the district line count too (Flight Control, Strike Hangars).

Distances are straight lines from the middle of each door to the nearest wall of the building. All are planner assumptions for Jordan to confirm.

## 3. Security and services the port must have

| Need | Found in | Check |
|---|---|---|
| Health screening and quarantine | Port Health | ✅ |
| Departure security screening | Departures Terminal | ✅ |
| Cargo inspection | Cargo Customs, Customs & Border Hq, Cargo Teleport Hall | ✅ |
| Custody suite (holding cells) | Arrivals Police Post, Customs & Border Hq, Concourse Police Post, Bow Docks Police Post, Port Guard Station | ✅ |
| One command room for every hull door | Port Security Command | ✅ |
| Cargo transfer to Deck 8 (cargo teleport pads) | Cargo Teleport Hall | ✅ |

Every precinct has its own utility plant and service shaft.

## 4. What the planner adds (proposed)

Nothing: the district meets its program.

### After the additions

✅ Every check passes.

## 5. Left for Jordan

- Escape craft and lifeboats are not designed anywhere on the ship yet, so the planner does not place any.
- Room plans, heights and looks of the new items are not designed yet.

## 6. Decided by Jordan

- 28 Nov 2026: the Stern Docks had no free land near their far berths, so the Stern Harbourmaster (P3-10) got a two-bay fire appliance bay and a border post at its stern end.
- 28 Nov 2026: the freight gate goes at the Port's bow end, F34 to F36, on the hull above Deck 8's Foundry Line and near its Deep Holds. P1-16 Freight Gate has 3 cargo berths, each 1,312 × 492 ft (400 × 150 m), with 919 ft (280 m) hull doors, plus a Freight Apron and a Freight Road.
- 28 Nov 2026: cargo goes on to Deck 8 by cargo-only teleport pads in the P4-17 Cargo Teleport Hall, 984 × 656 ft (300 × 200 m). No people use them. This is an exception to deck-to-deck travel happening only in the Spine Atrium.
- 28 Nov 2026: the Skiff Marina moved inland to a basin, 820 × 1,050 ft (250 × 320 m), with 25 slips, behind one Skiff Lock in the hull beside Medium Berth 1. The two planner skiff locks were removed.
