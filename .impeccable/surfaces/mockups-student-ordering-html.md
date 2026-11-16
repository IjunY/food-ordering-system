---
version: 1
slug: "mockups-student-ordering-html"
primary_target: "mockups/student-ordering.html"
related_targets: []
---

# Student ordering (interactive mockup)

Scope: a self-contained, clickable HTML mockup of the student app (not the production app). Mode: Operate. Phone-first (390 wide), shown in a device frame on desktop with a demo-controls panel beside it (the panel is not part of the app).

Audience and job: NTHU students ordering ahead between classes; sign in, pick a stall, customise items, check out, show the pass at the counter when it reads ready.

Screens: sign in, sign up (student ID 9 digits; password letters+numbers, ≥8, both required), onboarding (1 payment method, 2 notifications), stalls home (area tabs 全部/水木/小吃部/風雲, stall grid), stall menu (header B: photo + overlapping card; item grid), item page (option checkboxes incl. pick-one groups, notes, quantity, add to cart), checkout, full order pass, my orders, my account (ID card, notifications switch, language, change password, payment methods list with default/add/remove, sign out).

Content: all stalls, items, options, prices, pickup codes and descriptions are sample data and labelled SAMPLE DATA; payment, account and notification permission are mockups and say so. One language at a time (zh-TW / en) via a toggle. No vendor numbers shown anywhere.

Open (do not invent): pickup code format, wait-time estimate (omitted), live-update transport, payment provider and supported wallets, real vendor list/photos/options.

## Direction contract

THESIS: The order is a boarding pass, now in a colourful, lively NTHU-purple app. The pass is the loudest object; everything else is a friendly, photo-led ordering tool on a near-white lilac ground. Refuses the delivery-app default of orange accents and floating carts.

OWN-WORLD: Purple shell (#5B2A86 header, CTAs, active tabs, steppers), near-white lilac ground (#FAF8FC), white cards with soft purple-tinted shadows, sun-yellow (#FFC23D) accent for the code prefix, preparing chip and badges. Status bands: purple (default), green (ready), grey (cancelled). Small radii (pills 10px, cards 8px, fields 6px) except the pickup pass at 14px. Archivo condensed for numerals and labels; Noto Sans TC for all Chinese and body text. Photo placeholders tinted per stall in purple shades.

STORY: The student signs in with a student ID, sees open stalls by area, customises a dish, checks out with a saved payment method, and watches the pass turn green.

FIRST VIEWPORT: Purple header (title, 中|EN). Active mini passes first: purple band, white code with yellow letter, vendor name beside it, large status chip right; perforation; four legs. Then 所有攤位 with area tabs and a two-column stall grid. Three-tab bar (攤位 / 我的訂單 / 帳號).

FORM: User-pinned direction (ticket + departure board, purple) chosen after a bolder re-roll, then iterated live by the user toward colourful/lively. seed:3818d2e4f9be775f. Signature interaction: status changes snap in a stepped 90 ms two-frame step on the pass, never a fade.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
