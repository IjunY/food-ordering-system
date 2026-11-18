---
name: NTHU Food Ordering System
description: Order-ahead campus food for NTHU students; the order is a boarding pass in a lively NTHU-purple app.
colors:
  nthu-purple: "#5B2A86"
  purple-deep: "#45206A"
  purple-tint: "#F1EBF7"
  lavender: "#D9C8EE"
  sun-yellow: "#FFC23D"
  sun-ink: "#3D2A00"
  ready-green: "#17703F"
  cancel-grey: "#8A8395"
  alert-red: "#B42828"
  red-tint: "#FBEDED"
  success-tint: "#E8F5EC"
  lilac-ground: "#FAF8FC"
  card-white: "#FFFFFF"
  ink: "#1B1426"
  mute: "#655E70"
  faint: "#B3ABBD"
  hairline: "#E6E1EC"
  field-stroke: "#D5CDDF"
  control-off: "#CFC6DA"
  fill: "#F7F5FA"
typography:
  code-display:
    fontFamily: "Archivo, Noto Sans TC, sans-serif"
    fontSize: "84px"
    fontWeight: 800
    lineHeight: 0.9
    letterSpacing: "0.01em"
    fontVariation: "'wdth' 78"
  code-mini:
    fontFamily: "Archivo, Noto Sans TC, sans-serif"
    fontSize: "40px"
    fontWeight: 800
    lineHeight: 0.9
    letterSpacing: "0.01em"
    fontVariation: "'wdth' 78"
  headline:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.25
  title:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.3
  title-sm:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.45
  body-sm:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  status-chip:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1
  price:
    fontFamily: "Archivo, Noto Sans TC, sans-serif"
    fontSize: "19px"
    fontWeight: 600
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 78"
  total:
    fontFamily: "Archivo, Noto Sans TC, sans-serif"
    fontSize: "28px"
    fontWeight: 800
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 78"
  label:
    fontFamily: "Archivo, Noto Sans TC, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.16em"
  label-zh:
    fontFamily: "Archivo, Noto Sans TC, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
rounded:
  tag: "4px"
  tag-lg: "5px"
  field: "6px"
  card: "8px"
  pill: "10px"
  pass: "14px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "12px"
  inset: "16px"
  gutter: "20px"
  section: "28px"
components:
  button-primary:
    backgroundColor: "{colors.nthu-purple}"
    textColor: "{colors.card-white}"
    rounded: "{rounded.pill}"
    padding: "0 24px"
    height: "56px"
  button-primary-hover:
    backgroundColor: "{colors.purple-deep}"
  button-primary-disabled:
    backgroundColor: "{colors.control-off}"
    textColor: "{colors.card-white}"
  button-outline:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.nthu-purple}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "56px"
  button-outline-hover:
    backgroundColor: "{colors.purple-tint}"
  button-signout:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.alert-red}"
    rounded: "{rounded.pill}"
    height: "52px"
  button-signout-hover:
    backgroundColor: "{colors.red-tint}"
  stepper:
    backgroundColor: "{colors.nthu-purple}"
    textColor: "{colors.card-white}"
    rounded: "{rounded.pill}"
    height: "40px"
  input:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "0 4px 0 14px"
    height: "52px"
  option-row:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "14px"
  card:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "10px 12px 12px"
  chip-info:
    backgroundColor: "{colors.purple-tint}"
    textColor: "{colors.purple-deep}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  chip-sold-out:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card-white}"
    rounded: "{rounded.pill}"
    padding: "3px 9px"
  chip-in-cart:
    backgroundColor: "{colors.nthu-purple}"
    textColor: "{colors.card-white}"
    rounded: "{rounded.tag-lg}"
    padding: "3px 8px"
  badge-orders:
    backgroundColor: "{colors.sun-yellow}"
    textColor: "{colors.sun-ink}"
    rounded: "{rounded.tag-lg}"
    height: "18px"
    typography: "{typography.label}"
  pass-band:
    backgroundColor: "{colors.nthu-purple}"
    textColor: "{colors.card-white}"
    rounded: "{rounded.pass}"
    padding: "14px 16px 16px"
  pass-band-ready:
    backgroundColor: "{colors.ready-green}"
    textColor: "{colors.card-white}"
  pass-band-cancelled:
    backgroundColor: "{colors.cancel-grey}"
    textColor: "{colors.card-white}"
  status-chip:
    backgroundColor: "rgba(255,255,255,0.16)"
    textColor: "{colors.card-white}"
    rounded: "{rounded.pill}"
    padding: "8px 14px"
    typography: "{typography.status-chip}"
  status-chip-preparing:
    backgroundColor: "{colors.sun-yellow}"
    textColor: "{colors.sun-ink}"
  status-chip-ready:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.ink}"
  status-chip-cancelled:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.ink}"
  header:
    backgroundColor: "{colors.nthu-purple}"
    textColor: "{colors.card-white}"
    padding: "12px 16px 12px 20px"
    height: "64px"
  tab-bar:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.mute}"
  tab-bar-active:
    textColor: "{colors.nthu-purple}"
  note:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag-lg}"
    padding: "12px 14px"
  note-error:
    backgroundColor: "{colors.red-tint}"
    textColor: "#7E1C1C"
  note-success:
    backgroundColor: "{colors.success-tint}"
    textColor: "#0F4D2A"
---

# Design System: NTHU Food Ordering System

## Overview

**Creative North Star: "The Purple Boarding Pass"**

Every order becomes a ticket. The pickup pass is the loudest object on any screen: a purple band carrying a huge condensed code with a sun-yellow prefix letter, a status chip big enough to read at arm's length, a perforation, and four progress legs. Around it sits a friendly, photo-led ordering tool on a near-white lilac ground, wrapped in a purple shell (header, primary buttons, active tabs, steppers). The mood is colourful and lively but never noisy: one strong hue, one warm accent, white cards that float on soft purple-tinted shadows.

Density is phone-first and thumb-sized: a single 390px-wide column, 20px gutters, two-column card grids, 44px minimum touch targets, a three-tab bar at the bottom. Type splits cleanly in two: Archivo, condensed to width 78, speaks every numeral, code, price and small field label; Noto Sans TC speaks every word of Chinese and all body text. Status changes do not fade; they snap.

The world refuses the delivery-app default of orange accents and floating carts. Cart presence is shown inline (counts on stall cards, an "in cart" badge on item photos, the checkout CTA), never as a floating button.

**Key Characteristics:**
- Purple shell (header, CTAs, active tabs, steppers) over a near-white lilac ground.
- White cards with soft, two-layer, purple-tinted shadows; no borders on cards.
- Sun-yellow is a small, deliberate accent tied to the pass and to progress.
- Status bands: purple by default, green when ready, grey when cancelled.
- Small radii (10 / 8 / 6 / 4-5px); only the pickup pass is rounder (14px).
- Condensed Archivo numerals beside Noto Sans TC text; one language at a time.
- A stepped 90ms two-frame snap on status change, never a fade.

## Colors

One saturated university purple carries the shell and every primary action; a single sun-yellow accent marks the pass and progress; green, grey and red are reserved for order state and errors.

### Primary
- **NTHU Purple** (nthu-purple): the shell. Header bar, auth and onboarding hero bands, primary CTAs, steppers, active tab text and underline, checked checkboxes and radios, the switch when on, focus outlines, the default pass band and the ID card band.
- **Deep Purple** (purple-deep): CTA hover, text on purple-tint chips, selection text.
- **Purple Tint** (purple-tint): hover fill for outline buttons and links, info chips on the menu header, icon tiles in setting and option rows, the 3px focus halo around fields, the "default" payment chip.
- **Lavender** (lavender): small labels and secondary text on purple bands (pass labels on the purple band, the onboarding step counter, the ID card labels).

### Secondary
- **Sun Yellow** (sun-yellow): the prefix letter of a pickup code (and its echo in the auth hero headline), the preparing status chip and its progress leg, the orders badge in the tab bar, the active segments of the onboarding step bar, the glyph in the notification preview tile. Always on purple or carrying sun-ink text, never as text on white.
- **Sun Ink** (sun-ink): text on sun-yellow (preparing chip, orders badge).

### Tertiary
- **Ready Green** (ready-green): the ready pass band and its legs, open-status text on stall cards, valid-field borders, satisfied password checks, success-note icons.
- **Cancel Grey** (cancel-grey): the cancelled pass band. The code on it turns pale (#E9E5EE) with a 3px strike-through and the prefix letter goes white.
- **Alert Red** (alert-red): invalid-field borders and hints, "remove" links, sold-out warnings, the sign-out outline, offline status. **Red Tint** (red-tint) is the error-note ground and sign-out hover.
- **Success Tint** (success-tint): success-note ground.

### Neutral
- **Lilac Ground** (lilac-ground): the app background under every scrolling screen and the sticky area-tab strip.
- **Card White** (card-white): cards, list rows, the tab bar, inputs.
- **Ink** (ink): primary text; the sold-out chip ground; status-chip text on ready and cancelled bands.
- **Mute** (mute): secondary text, meta lines, inactive tabs, field labels on white.
- **Faint** (faint): disabled icon strokes.
- **Hairline** (hairline): row dividers, the tab-bar top rule, option-row borders, unfilled progress legs.
- **Field Stroke** (field-stroke): input and textarea borders at rest; the pass perforation and the dashed "add payment" rule.
- **Control Off** (control-off): switch off, checkbox and radio rings, disabled CTA ground, dashed placeholder-card borders.
- **Fill** (fill): neutral note ground and row hover on white.

### Named Rules
**The Purple Shell Rule.** Purple is the frame and the action: header, primary buttons, steppers, active tabs, checked controls. Body surfaces stay lilac and white so the shell reads as one object.

**The Sun Accent Rule.** Sun-yellow marks only the pass and progress: the code prefix, the preparing chip and leg, the orders badge, the onboarding step bar. It is never a general highlight colour and never text on a light ground.

**The Stall Tint Rule.** Each stall carries its own purple shade (the sample set spans #4A2370 to #9050C8), used only to tint its photo placeholder (12-16% over white for the ground, 65-70% for the icon, 75% toward black for the caption). It never becomes a badge, a band or a number tile. No vendor numbers appear anywhere.

## Typography

**Display Font:** Archivo, condensed (wdth 78), weights 500-800 (with Noto Sans TC fallback)
**Body Font:** Noto Sans TC, full weight range 100-900 (with system-ui, sans-serif)
**Label/Numeral Font:** Archivo condensed, tabular numerals

**Character:** a narrow, departure-board numeral face for everything that is counted or coded, beside a warm, even CJK sans for everything that is said. The condensed numerals let an 84px pickup code fit a phone width without shouting in width.

### Hierarchy
- **Code Display** (800, 84px, line-height 0.9, wdth 78): the pickup code on the full pass. The mini pass on home and orders sets it at 40px; the ID card at 40px with 0.03em tracking.
- **Headline** (700, 28px, 1.25): the auth hero headline only.
- **Title** (700, 22px, 1.3): onboarding step questions and the item page name; 20px for the auth card heading and the menu header stall name.
- **Header Title** (700, 18px): the purple header bar title, single line with ellipsis.
- **Status Chip** (Noto 700, 20px on the mini pass, 26px on the full pass, line-height 1): the pass status word, white-space nowrap.
- **Body** (400, 16px, 1.45): default text, option labels, input values (inputs at 17px). Secondary body at 15px (descriptions, leads, list text) and meta at 13px in mute.
- **Price** (Archivo 600, 19px on item cards, 18px on checkout lines, 24px on the item header, tabular): unit prices. **Total** (Archivo 800, 28px): checkout total; the CTA amount is Archivo at 22px.
- **Label** (Archivo 700, 11px, 0.16em, uppercase in English; 12px, 0.04em in Chinese): field labels on the pass and ID card (取餐碼/PICKUP, 狀態/STATUS, 攤位, 地點, 下單), and the SAMPLE DATA tag.
- **Tab Bar** (12px; 700 when active).

### Named Rules
**The Two Voices Rule.** Archivo condensed speaks numerals, codes, prices, counts and small field labels; Noto Sans TC speaks every word. Chinese never falls to a system face: Noto Sans TC is set explicitly on html, body, button, input, textarea, select, legend, label and on input and textarea placeholders, because form controls do not inherit fonts.

**The Two Prices Rule.** Unit prices read "$120": on item cards, the item page header, checkout lines and pass lines. Totals read "NT$": the checkout total, every CTA amount (add to cart, place order) and order history rows.

**The One Language Rule.** Exactly one language shows at a time, switched by the 中|EN toggle in the header (or the account language row). Labels never pair Chinese and English side by side.

## Layout

A single phone column, 390px wide in the reference frame, filling the viewport on a real phone. Each screen is a fixed purple header (min-height 64px), a scrolling main area on the lilac ground, and either a bottom CTA or the three-tab bar; safe-area inset pads the tab bar.

Horizontal rhythm is a 20px gutter for sections, grids and list rows; cards that overlap a photo or hero band (menu header card, auth card) sit 16px from the edges. Two-column grids (stalls, items) use a 12px gap; stacked cards use 10px. Section headings get 28px above and 10px below. Card bodies pad 10-12px; pass bands 14-16px (20/18px on the full pass); setting and option rows 14px vertical by 16px.

Overlap is the recurring move: the menu header card rides 44px up over the stall photo and the auth card rides 36px up over the purple hero band, each with a stronger shadow. Area tabs stick to the top of the scroll on the lilac ground.

## Elevation & Depth

Depth is soft and ambient. Every white surface lifts off the lilac ground with a two-layer shadow: a tight neutral contact shadow plus a wider purple-tinted bloom. Hover deepens the bloom; nothing uses borders to separate cards, and nothing uses a hard offset shadow.

### Shadow Vocabulary
- **Card rest** (`box-shadow: 0 1px 2px rgba(27,20,38,.06), 0 4px 14px rgba(91,42,134,.08)`): stall cards, item cards, account groups.
- **Card hover** (`box-shadow: 0 1px 2px rgba(27,20,38,.08), 0 8px 22px rgba(91,42,134,.16)`): clickable stall and item cards on hover.
- **Pass / ID card** (`box-shadow: 0 1px 2px rgba(27,20,38,.06), 0 6px 18px rgba(91,42,134,.10)`): the pickup pass and the account ID card; the mini pass deepens to `0 10px 24px rgba(91,42,134,.16)` on hover.
- **Overlap** (`box-shadow: 0 1px 2px rgba(27,20,38,.06), 0 8px 24px rgba(91,42,134,.12)`): the auth card and notification preview; the menu header card uses `0 6px 18px` at .12.
- **Quiet group** (`box-shadow: 0 1px 2px rgba(27,20,38,.06), 0 4px 14px rgba(91,42,134,.06)`): option groups and the quantity row on the item page.
- **Field focus halo** (`box-shadow: 0 0 0 3px #F1EBF7`): inputs and the notes box on focus, with a purple border.

### Named Rules
**The Tinted Bloom Rule.** Shadows are always two layers and the outer layer is purple at 6-16% alpha. A grey-only or single-layer shadow is off-world.

## Shapes

Small, friendly radii in a strict ladder: pills and buttons 10px (CTAs, outline buttons, steppers, chips, status chips, the language toggle, the switch track), cards 8px (stall and item cards, menu header card, auth card, account groups, ID card), fields and option rows 6px (inputs, notes box, onboarding options, icon tiles, dashed placeholders), small tags 4-5px (the orders badge, in-cart badge, area counts, checkbox squares, notes, link hover). Round shapes are reserved for radio dots, the switch knob and the spinner.

**The Ticket Exception Rule.** Only the pickup pass is rounder (14px). Its single dashed perforation is notched with two half-circle cut-outs in the ground colour, and every purple band (pass, ID card, auth hero) carries one faint white ring (rgba 255,255,255 at .07) bleeding off its top-right corner.

## Components

### Buttons
Confident, full-width, purple.
- **Shape:** 10px radius.
- **Primary (CTA):** purple ground, white 17px bold text, 56px tall, 24px side padding; when it carries an amount it splits label left and NT$ total right in Archivo 22px. Hover goes deep purple; disabled goes control-off; busy shows an 18px white spinner.
- **Outline:** white ground, 1.5px purple border, purple bold text (onboarding Back at 56px, "change" at 36px); hover fills purple-tint.
- **Sign-out:** 52px, white with a 1.5px red outline and red bold text; hover fills red-tint.
- **Text links:** purple or ink bold with a 3px-offset underline; 44px-class hit area via padding.
- **Add (+) square:** 40px, 6px radius, 1.5px purple border on white.

### Stepper
Purple, 10px radius, 40px tall (36px inside item cards), white minus/plus buttons with a 16% white hover and a tabular Archivo count between them. Disabled ends drop to 40% opacity.

### Chips
- **Info chip:** purple-tint ground, deep-purple 12px text, 10px radius (menu header facts: open state, location, hours).
- **Sold-out (售完):** ink ground, white bold 12px, top-left on the item photo; 14px at 5px radius on the item page.
- **In-cart ("已加入 N"):** purple ground, white bold 12px, 5px radius, top-right on the item photo.
- **Default payment:** purple-tint ground, purple bold 11px, 10px radius.
- **Pick-one tag:** 11px mute text in a 1px hairline box, 4px radius, beside the option name.

### Cards / Containers
- **Corner Style:** 8px.
- **Background:** white on the lilac ground.
- **Shadow Strategy:** Card rest, deepening to Card hover (see Elevation).
- **Border:** none.
- **Stall card:** 4:3 tinted photo placeholder with a centred photo icon and caption, then name (16px bold), meta (12px mute), and a status row (open in green, closed in mute, cart count in purple). Closed stalls grey out the image.
- **Item card:** the whole card is one button that opens the item page; 4:3 tinted photo, two-line name (15px, min-height 2.7em), Archivo price and a 36px add square. Sold-out items strike the price and grey the image.

### Inputs / Fields
- **Style:** 52px tall, white, 1.5px field-stroke border, 6px radius; values 17px (student ID in Archivo at 85% width with 0.06em tracking, 20px). Labels 14px bold above; hints 13px mute below; eye toggle 44px.
- **Focus:** purple border plus a 3px purple-tint halo.
- **Error / Valid:** red border with a red hint, or green border. Validation runs live as the student types without stealing focus.
- **Password checklist:** two-column list of rules, mute with an icon, turning green and medium weight when met.
- **Notes box:** textarea in the same style with a right-aligned "n / 60" counter.

### Option rows (onboarding)
Full-width 6px-radius rows with a 1.5px hairline border: 40px purple-tint icon tile, bold title with mute sub-line, and a 22px radio. Selected rows take a purple border, a #FBF8FE ground and a purple dot.

### Item options (item page)
Options sit in white groups (8px, quiet shadow) with a bold legend and a 12px mute sub-line. Each row is a 22px checkbox square (5px radius, purple when checked with a white tick), label and mute price delta. Pick-one groups replace each other's choice. Below: notes box with counter, a quantity row with stepper, and the add-to-cart CTA showing the live NT$ total.

### Navigation
- **Header:** purple bar, back button 44px with a 14% white hover, 18px bold title, 中|EN segmented toggle (white outline at 45%, active segment white with purple text). Focus outlines turn white inside the header.
- **Tab bar:** white, hairline top rule, three equal tabs (攤位 / 我的訂單 / 帳號) with icon over 12px label; active is purple and bold. The orders tab carries the sun-yellow badge.
- **Area tabs:** 全部 / 水木 / 小吃部 / 風雲 with a small Archivo count chip on white; active tab is purple bold with a 3px purple underline and a purple count chip.
- **Onboarding head:** purple band with a two-segment step bar (active segments sun-yellow, rest white at 25%), an Archivo step counter in lavender, and a footer pairing an outline Back with the primary button.

### Notes
5px radius, 12px 14px padding, 14px text with an optional bold underlined action pushed right. Neutral on fill; error on red-tint with dark red text (announced as an alert); success on success-tint with dark green text and a green icon.

### Account
An ID card (purple band at 8px with Archivo 40px student ID and lavender labels over white fields), then white groups of setting rows (40px purple-tint icon tile, title and mute sub-line, trailing control). The switch is a 52 by 32 track at 10px radius, purple when on, with a 26px white knob sliding 20px. Payment methods list each method with a default chip and set-default / remove links, closed by a dashed "add" row in purple. The red outlined sign-out closes the screen.

### Pickup Pass (signature)
The order is a boarding pass.
- **Band:** purple by default, green when ready, grey when cancelled; white Archivo code with the sun-yellow prefix letter (the prefix stays yellow on green; it turns white on grey).
- **Status chip:** 10px radius. Confirming is white at 16% over the band with white text; preparing is sun-yellow with sun-ink; ready and cancelled are white with ink text. Labels on the green and grey bands are white; on purple they are lavender.
- **Mini pass:** 40px code, vendor name beside the code (15px bold white, wraps to two lines), a large 20px status chip at the right.
- **Full pass:** the 84px code on its own, the 26px status chip on its own row beneath, then a white field strip (攤位 / 地點 / 下單), one perforation, four progress legs, and the order lines (unit "$" per line, "NT$" total).
- **Legs:** four 4px bars with 12px captions; done legs purple (green when ready), the current leg purple when confirming, sun-yellow when preparing.
- **Motion:** on a status change the chip and current legs snap in two steps over 90ms (opacity .3 and 2px down, then rest); this is the system's signature interaction and switches off under reduced motion.

### Behaviour shared by all screens
Focus is restored to the same control after every re-render; on a screen change it moves to the new screen's heading. All announcements (status changes, quantity, toggles) go through one persistent polite live region, batched. `prefers-reduced-motion` disables every animation and transition. Sample content carries a SAMPLE DATA tag, and payment, account and notification-permission screens say they are mockups.

## Do's and Don'ts

### Do:
- **Do** keep the shell purple (#5B2A86) and the ground lilac (#FAF8FC); put content on white cards with the two-layer purple-tinted shadow.
- **Do** keep sun-yellow (#FFC23D) to the code prefix, the preparing chip and leg, the orders badge and onboarding progress, always with sun-ink text when it is a ground.
- **Do** switch the pass band by state: purple default, green ready, grey cancelled; keep the status chip on ready and cancelled white with ink text.
- **Do** follow the radius ladder: 10px pills and buttons, 8px cards, 6px fields and option rows, 4-5px tags, 14px only for the pickup pass.
- **Do** set numerals, codes, prices and field labels in Archivo condensed (wdth 78) and every word in Noto Sans TC, including form controls and placeholders.
- **Do** write unit prices as "$120" and totals, CTA amounts and order history as "NT$".
- **Do** snap status changes in the stepped 90ms two-frame step, and turn it off under reduced motion.
- **Do** restore focus across re-renders, move it to the heading on a screen change, and announce through the single live region.
- **Do** label placeholder content SAMPLE DATA and mark mocked payment, account and permission flows as mockups.

### Don't:
- **Don't** use orange accents or a floating cart button; show cart state inline.
- **Don't** show vendor or stall numbers anywhere; a stall's purple shade only tints its photo placeholder.
- **Don't** fade or slide status changes; the change snaps.
- **Don't** use sun-yellow as text on white or lilac, or as a general highlight.
- **Don't** separate cards with borders or use grey-only, single-layer or hard offset shadows.
- **Don't** show Chinese and English side by side; one language at a time via the 中|EN toggle.
- **Don't** let form controls fall back to a system CJK face.
