---
type: is
id: is-01m1xxzghvbt8ek87w822rfxyh
title: "Amharic deck: YouTube is primary, Deezer is opportunistic"
kind: feature
status: closed
priority: 0
version: 2
labels:
  - deck
  - audio
dependencies: []
created_at: 2026-09-07T12:37:36.954Z
updated_at: 2026-09-07T12:44:11.834Z
closed_at: 2026-09-07T12:44:11.833Z
close_reason: "Superseded by hitster-4mea: the 37% figure was measured with the wrong Deezer endpoint (/search/artist). Field-scoped track search gives 87%."
resolution: null
duplicate_of: null
---
CORRECTS an earlier finding. FINDINGS.md F6 claimed "Deezer's Ethiopian catalogue is
real" on the basis that six artist searches each returned a track with a preview. That
check was too weak: it did not verify the returned artist actually matched.

Measured properly across 24 major Amharic artists — counting only artists with playable
top tracks correctly attributed:

  PLAYABLE: Aster Aweke, Mahmoud Ahmed, Mulatu Astatke, Alemayehu Eshete,
            Hailu Mergia, Girma Beyene, Rophnan, Zeritu Kebede, Esubalew Yetayew
  ABSENT:   Teddy Afro, Tilahun Gessesse, Bizunesh Bekele, Neway Debebe,
            Ephrem Tamiru, Betty G, Jano Band, Dawit Tsige, Abby Lakew,
            Hachalu Hundessa, Munit Mesfin, Tsedenia Gebremarkos, Michael Belayneh

~37% playable, and the hits skew almost entirely to the Ethiopiques reissue catalogue
(1960s-70s Ethio-jazz, licensed in Europe). Contemporary Amharic pop is largely absent.
"Teddy Afro" resolves to an unrelated artist, "Teddy Karo", with 0 playable tracks.

Consequence: for an Amharic deck, YouTube is the PRIMARY source and Deezer is the
opportunistic one (used when a correctly-attributed track exists, for lighter bandwidth
and no video).

Also: Amharic-script search on Deezer barely works — "አስቴር አወቀ" and "ማህሙድ አህመድ" both
return zero results. Search by Latin transliteration; store the Amharic title separately
for display.
