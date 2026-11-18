---
version: 1
slug: "frontend-index-html"
primary_target: "frontend/index.html"
related_targets: ["frontend/css/app.css","frontend/js/components.js","frontend/js/pages/customer.js","frontend/js/pages/admin.js"]
---

# Frontend app (student, vendor and admin screens)

Scope: the shipped plain HTML/CSS/JS frontend in `frontend/`, served by the backend at `/`. Mode: Operate. Student screens are phone-first (one column, max 30rem); vendor and admin screens are desktop/tablet-first.

Audience and job: students ordering ahead and watching one status; vendor staff advancing orders at a busy counter; an admin approving or suspending restaurants.

Screens: sign in, sign up, stalls home (active passes, search, sort, area tabs, stall grid), stall menu, item page, review order, payment (simulated), payment done, order pass, my orders, my account; vendor order board, menu management, store settings, reports; platform admin.

Constraints: existing routes, API wiring and features stay. Restaurants and menus are still demo data and carry the SAMPLE DATA tag. Mockup-only flows with no backend are not built: onboarding, saved payment methods, change password, notification switch. Student ID accepts letters and digits (staff and admin accounts sign in on the same page). Light theme only.

Open: pickup code format, live-update transport (currently polling), payment provider.

## Direction contract

THESIS: The order is a boarding pass in a colourful NTHU-purple app, carried over unchanged from `mockups/student-ordering.html`. Refuses the delivery-app default of orange accents and floating carts, and the previous receipt-paper look.

OWN-WORLD: Purple shell (#5B2A86 header, CTAs, active tabs, steppers) on a lilac ground (#FAF8FC); white cards with two-layer purple-tinted shadows and no borders; sun-yellow (#FFC23D) only for the code prefix and progress; status bands purple, green (ready), grey (cancelled); radii 10/8/6/4-5px with 14px only on the pass; Archivo condensed for numerals and labels, Noto Sans TC for all words.

STORY: The student signs in, sees their passes first, picks a stall, customises a dish, pays, and watches the pass turn green. The vendor sees the same pass as a kitchen ticket and moves it column to column.

FIRST VIEWPORT: Purple header (title, 中|EN). Active mini passes first. Then 所有攤位 with SAMPLE DATA, a compact search and sort row, area tabs with counts, and a two-column stall grid. Three-tab bar with the yellow orders badge.

FORM: User-pinned direction inherited from the mockup's contract. seed:3818d2e4f9be775f. Signature interaction: the 90 ms two-step snap on the status chip and legs when an order's status changes, on student passes and on new kitchen tickets.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
