# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

- Backend (existing): FastAPI, SQLAlchemy 2, Alembic migrations, PostgreSQL, run via Docker Compose; Python ≥ 3.12, managed with uv.
- Frontend (decided, not yet built): a React + Vite single-page app that talks to the FastAPI JSON API.

## Users

- **Students (primary).** NTHU students ordering campus food on their phones, often between classes or while walking across campus. Their job: get lunch without standing in the peak-hour queue.
- **Vendors (secondary).** Campus food vendors running a counter during service. They use a laptop or tablet at the counter to confirm incoming orders, move them through preparation, and hand them over.
- **Admins (tertiary).** Manage the system (an `admin` module exists in the backend, but its scope has not been defined yet).

## Product Purpose

Let students skip the lunch queue: order ahead from a campus vendor, then walk over and pick up when the order is marked ready. Success means less waiting at peak hours for students and a clear, manageable flow of orders for vendors.

The project is also the final project for NTHU's Introduction to Programming I (I2PI) course.

## Positioning

A campus-specific order-ahead system for NTHU vendors. Students see real-time order status and come to the counter only when their food is ready.

## Operating Context

- Peak usage is around lunch, when queues are longest. Students check their order status on a phone and time the walk to the vendor.
- Order lifecycle (from `app/orders/states.py`): `confirming → preparing → ready → picked up`, with `cancelled` as an exit. The vendor advances each step; the student watches it change.
- Each menu item belongs to a vendor and has a name, a price (stored as an integer), and an availability flag the vendor can toggle.
- An order records who created it, when, and its line items (quantity plus the unit price at the time of the order).

## Capabilities and Constraints

- Confirmed: multiple vendors, per-item availability, order-ahead with status tracking, pickup at the vendor.
- Planned: online payment (the `payments` module exists but is empty; provider and flow are undecided).
- Authentication (decided): students sign in with student ID + password. Sign-up asks for a student ID (exactly 9 digits) and a password (letters and numbers only, containing both, at least 8 characters). After sign-up, a short onboarding asks the student to add a payment method and to allow notifications (for order-ready alerts). Backend `auth` module is still empty.
- Open: the payment provider and supported methods, the scope of admin features, and the currency display format.
- Device split: the student UI is phone-first; the vendor UI is desktop/tablet-first.

## Brand Commitments

- Working name: "Food Ordering System" (NTHU). There is no logo or other brand assets yet.
- Bilingual interface: Traditional Chinese and English, for local and international students. One language is shown at a time; the user switches with a language toggle (no side-by-side bilingual labels).

## Evidence on Hand

- There is no real vendor list, menu data, photography, usage figures, or testimonials yet. Future work must not invent vendor names, menus, prices or adoption claims and present them as real. Placeholder data must be clearly marked as sample data.

## Product Principles

1. **Status is the product.** A student's main question is "is it ready?"; order state must be legible at a glance, on a phone, on the move.
2. **Peak-hour speed for both sides.** Students reorder in a few taps; vendors advance orders with no hesitation during a rush.
3. **Honest availability.** What is shown as orderable must actually be available. Sold-out items and cancellations are explicit, never silent.
4. **Two languages, one experience.** Traditional Chinese and English are both first-class and shown one at a time via a toggle; neither is an afterthought translation.

## Accessibility & Inclusion

- Bilingual (zh-TW / en) content, one language displayed at a time with a toggle; layouts must hold up with both scripts and differing text lengths.
- The student UI must work on a phone used one-handed and outdoors; the vendor UI must be readable from a glance at a busy counter.
- No formal conformance target has been set; WCAG 2.2 AA is the working assumption until one is decided.
