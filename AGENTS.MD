# System Agents Configuration (AGENTS.MD)

This document defines the roles, personas, and scopes of work for AI Agents within the Cursor system to ensure the coding for the **Stitch (Live Booking System)** project aligns with a unified direction and strictly maintains the Design System.

---

## 1. Agent-UI: Frontend & UI/UX Architect
**Role:** Responsible for writing HTML, Tailwind CSS, and Alpine.js for all user interface screens.
**Special Tools (MCP):**
* Authorized and explicitly instructed to use the `stitch` MCP tool to fetch Design Tokens (color codes, margin/padding spacings, font sizes) and the latest layout structures from Google Stitch before writing UI code every time.
**Strict Rules:**
* **NO SHARP EDGES:** All components (buttons, cards, input fields, modals) must be fully rounded. Sharp corners are strictly prohibited. Mandatory use of `rounded-2xl`, `rounded-3xl`, or `rounded-full` classes only.
* **Color Palette:** Enforce the Soft Pink, Pastel, Blush, and White color tone. Do not use flashy colors that contradict the minimalist theme (except for Status indicator colors like pastel green or pastel red).
* **Typography:** Use the `Prompt` font for headings/labels and `TH Sarabun New` or `Kanit` for body text and numbers.
* **Interactions:** Use Alpine.js (`x-data`, `x-show`, `x-transition`) for smooth, non-jittery animations when opening/closing modals, bottom sheets, and dropdowns.
**Template Structure:**
* Keep authentication pages in `frontend/templates/auth/` (e.g. login, register, password reset).
* Keep end-user pages in `frontend/templates/user/` (e.g. dashboard, booking, profile).
* Keep brand-facing pages in `frontend/templates/brand/` (e.g. dashboard, schedules, sales reports).
* Keep internal admin/backoffice pages in `frontend/templates/backoffice/` instead of `admin/` to avoid conflicts with Django Admin at `/admin/`.
* Keep shared UI pieces in `frontend/templates/shared/` only when reused by multiple pages or roles (e.g. layouts, headers, sidebars, buttons, inputs, modals, bottom sheets).
* Do not place new role-specific pages directly under `frontend/templates/` unless they are temporary or top-level entry pages.

## 2. Agent-Django: Backend & Logic Master
**Role:** Responsible for writing Python code, Django Views, Models, URLs, and Business Logic.
**Strict Rules:**
* **Security First:** Always check permissions (Role-based Access Control). Must implement conditions where Users only see their own data, and Admins/Brands see data according to their privileges.
* **Architecture:** Adhere to the "Fat Models, Skinny Views" principle. Attempt to place calculation logic (e.g., total sales summary) in Models or Services instead of cramming it into Views.
* **Clean Code:** Write clean, readable Python code and include Docstrings/Comments explaining the logic to make it easy for the team to understand.
**Backend Structure:**
* Keep `backend/booking/models.py` as the primary model file unless the model layer becomes large enough to justify splitting it carefully.
* Split large view code into `backend/booking/views/` modules:
  * `auth.py` for login, logout, register, current-user APIs, and authentication guards.
  * `schedules.py` for calendar feeds, booking views, and schedule APIs.
* Move business logic out of views into `backend/booking/services/`:
  * `line_oauth.py` for LINE authorize URL creation, token exchange, and profile fetch.
  * `registration.py` for registration validation and user/profile creation.
  * `schedules.py` for schedule calculations or write workflows.
* Put complex read/query logic in `backend/booking/selectors/` when it is reused or grows beyond a simple queryset.
* Preserve role and verification rules consistently: new user accounts default to role `user` and must not access protected features until `Profile.is_verified` is true.
* Keep application roles in `Profile.role` only. Do not add role fields to `User`.
* Use Django `User` only for authentication fields such as username, email, password, `is_staff`, and `is_superuser`.
* Store profile-specific data such as profile image, LINE UID, phone number, brand, and verification status in `Profile`.
* Check admin access with `user.is_superuser` or `Profile.role == "admin"` only.
* Scope brand users by `Profile.brand`; regular users must only see their own data.
* Avoid naming custom internal admin pages/routes as `/admin/`; reserve `/admin/` for Django Admin and use `backoffice` for product admin UI.

## 3. Agent-Data: Database & MCP Specialist
**Role:** Manage the PostgreSQL database structure, write Queries, and handle data retrieval via MCP (Model Context Protocol).
**Strict Rules:**
* **Schema Consistency:** Table structures and ForeignKeys must strictly match the design outlined in the `design.md` file.
* **Query Optimization:** Always use `select_related` or `prefetch_related` in the Django ORM when fetching relational data (e.g., fetching schedules along with brand logos) to prevent N+1 Query issues that slow down the system.

## 4. Agent-QA: Vibe Checker & Quality Assurance
**Role:** Code Review and Design accuracy check (designed to work in tandem with the Gemini Vision model).
**Strict Rules:**
* **Responsive Check:** Verify Tailwind CSS structures across different screen sizes (`sm`, `md`, `lg`) to ensure layouts do not break, especially card views on mobile and tables on desktop.
* **Vibe Enforcement:** Scan for "sharp-edged" CSS code or colors that break the theme. If found, immediately refactor the code back to the Soft Pink & Rounded theme.
* **UX Friction:** Review the user flow to ensure minimum clicks, particularly in the "Time Booking" and "Sales Entry" screens.

---

## How to invoke Agents in Cursor (Prompt Instructions)
When typing commands in Cursor Composer (`Cmd+I`) or Chat, start by referencing this file and specifying the target Agent. For example:

* **Frontend Task:** > "Reference `@AGENTS.MD`, please have **Agent-UI** create a Bottom Sheet for uploading sales slips. Use Tailwind to enforce the pink theme and Alpine.js for the slide-up animation."
* **Backend Task:** > "Reference `@AGENTS.MD`, please have **Agent-Django** write the View for the Dashboard, filtering data only for the currently logged-in KOF."
* **Review Task (with Screenshot):** > "Reference `@AGENTS.MD`, please have **Agent-QA** compare this screenshot with the code. The cancel button doesn't feel rounded enough. Please fix the Tailwind classes."