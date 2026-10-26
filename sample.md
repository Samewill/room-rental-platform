# Room Rental Platform: Development Roadmap

My recommendation is to build your platform **one small, working feature at a time**, using Neon for PostgreSQL, GitHub for version control, and GitHub Copilot as your coding assistant.

Don't try to build the entire website, WhatsApp bot, database, and AI agent simultaneously. Instead, complete one small part, test it, understand it, and then move on.

Your development process will look like this:

**Design → Implement → Test → Review → Commit → Add the next feature**

This approach also helps you grow as an AI engineer because you'll learn how the database, backend, frontend, and AI services work together.

## 1. Choose a technology stack

For your first version, I'd recommend this stack.

| Component | Recommended technology | Purpose |
|---|---|---|
| Frontend | React + TypeScript | Website interface |
| Styling | Tailwind CSS | Responsive layouts and styling |
| Backend | Python + FastAPI | Business logic and API endpoints |
| Database | Neon PostgreSQL | Persistent application data |
| Database access | SQLAlchemy + Alembic | Python database models and schema migrations |
| Validation | Pydantic | Validate incoming API data |
| Testing | Pytest | Test backend functionality |
| Version control | Git + GitHub | Track changes and manage branches |
| AI coding assistant | GitHub Copilot | Assist with implementation and tests |
| AI integration | OpenAI API, when needed | Interpret natural-language requests |
| Messaging | WhatsApp Business Platform, later | Support WhatsApp interactions |

**Why FastAPI?** You're working toward AI engineering, and Python is useful for integrating machine-learning models and LLMs. FastAPI also provides a convenient way to build APIs that your frontend and AI services can call.

You don't need to use every technology immediately. Start with the backend and database, then connect the frontend.

---

# 2. Divide the platform into development phases

Your ERD and class diagram already identify the main parts of the system. We can turn those into a practical development plan.

## Phase 1: Set up the project

**Goal:** Create the project structure and establish a working connection between FastAPI and Neon.

Don't build any business features yet.

### Step 1. Create a GitHub repository

Name it:

`room-rental-platform`

Create these branches:

| Branch | Purpose |
|---|---|
| `main` | Stable, working version |
| `develop` | Integration branch for completed features |
| `feature/database-setup` | Initial database connection and configuration |
| `feature/listing-api` | First listing functionality |
| `feature/listing-ui` | Listing pages in the frontend |

You don't need to create every feature branch immediately. Create a branch when you're ready to work on that feature.

For each feature, follow this workflow:

1. Start from the latest `develop`.
2. Create a feature branch.
3. Implement one small piece.
4. Test it locally.
5. Commit the changes.
6. Merge it into `develop` after review.
7. Merge into `main` when the release is ready.

For a solo project, you can keep this lightweight. You don't need a complicated Git workflow.

### Step 2. Create your initial folder structure

I recommend a single repository containing both the frontend and backend.

```text
room-rental-platform/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── .env.example
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   │
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
│
├── docs/
│   ├── architecture.md
│   ├── database-design.md
│   └── development-roadmap.md
│
├── .gitignore
├── README.md
└── .github/
    └── copilot-instructions.md
```

This is the target structure, not a requirement to create every file on day one.

Start with only the files needed for the current feature. Let the rest grow as the project develops.

### Step 3. Understand the backend folders

These folders have different responsibilities.

| Folder | Responsibility | Example |
|---|---|---|
| `api/` | Defines HTTP endpoints | `GET /api/v1/listings` |
| `models/` | Defines database models | `Listing` |
| `schemas/` | Validates request and response data | `ListingCreate`, `ListingResponse` |
| `repositories/` | Handles database queries | Find listings by area |
| `services/` | Implements business rules | Validate listing publication |
| `core/` | Application configuration and security | Environment variables and authentication |
| `db/` | Database connection and shared configuration | SQLAlchemy session |
| `tests/` | Automated tests | Test listing creation |

For example, when a landlord creates a listing:

```text
React frontend
      |
      | POST /api/v1/listings
      v
FastAPI endpoint
      |
      v
Authentication and authorization
      |
      v
Listing service
      |
      v
Listing repository
      |
      v
SQLAlchemy
      |
      v
Neon PostgreSQL
```

Each layer has a job. This separation becomes especially useful when you add AI capabilities because the AI can call the same controlled business services as your normal application.

---

## Phase 2: Connect FastAPI to Neon

**Goal:** Make your backend communicate with your existing database.

Complete these tasks:

- [ ] Create a Python virtual environment.
- [ ] Install FastAPI and its development server.
- [ ] Install SQLAlchemy and a PostgreSQL driver.
- [ ] Install Alembic for database migrations.
- [ ] Store the Neon connection string in an environment variable.
- [ ] Create a database session.
- [ ] Add a health-check endpoint.
- [ ] Test the connection.

Your first endpoint should be simple:

`GET /health`

Expected response:

```json
{
  "status": "ok"
}
```

You can then add a database health check that executes a simple query, such as `SELECT 1`.

Keep these checks separate: the first confirms the API is running, while the second confirms it can communicate with PostgreSQL.

### Important Neon connection rule

Neon provides a connection string for your PostgreSQL database.

Store it in your backend's `.env` file during local development:

```text
DATABASE_URL=your_neon_connection_string
```

Never commit `.env` to GitHub.

Your `.gitignore` should include:

```gitignore
.env
.env.*
!.env.example

__pycache__/
.venv/
node_modules/
dist/
```

Keep `.env.example` free of real passwords and connection strings.

For a production deployment, use your hosting platform's secret-management facility rather than uploading your local `.env` file.

### Your first milestone

At the end of this phase, you should be able to:

1. Start FastAPI locally.
2. Open its API documentation.
3. Call `GET /health`.
4. Confirm that a separate endpoint can connect to Neon.

FastAPI provides interactive API documentation at `/docs` by default.

Don't proceed to the listing feature until these basics work.

---

# Phase 3: Build your first actual feature — public room listings

**This should be your first functional branch of the website.**

Why start here?

Your platform's main purpose is to help tenants discover available rooms. You can build a useful part of the product without immediately implementing authentication, payment processing, WhatsApp, or AI.

The first version should allow a visitor to:

- View available rooms.
- See the rent and location.
- Open a room's details.
- Filter listings by a few basic criteria.

Initially, use manually inserted test data. You can add landlord accounts and listing creation later.

### Step 1. Prepare the database tables

You already started with the identity tables.

Next, create:

**`areas`**

Stores neighborhoods or campuses.

**`listings`**

Stores room information, including:

- `listing_id`
- `landlord_id`
- `area_id`
- `title`
- `description`
- `room_type`
- `monthly_rent`
- `deposit_amount`
- `address`
- `date_available`
- `status`
- `created_at`

**`listing_photos`**

Stores references to photos associated with listings.

**`amenities`** and **`listing_amenities`**

Represent features such as Wi-Fi, parking, and furnished rooms.

Use PostgreSQL's `NUMERIC` type for monetary values instead of floating-point types. For example, `NUMERIC(10,2)` can represent a rent amount with two decimal places.

Make `landlord_id` a foreign key to `users.user_id`, and `area_id` a foreign key to `areas.area_id`.

However, remember that a foreign key only verifies that a user exists. Your application must later verify that the user is authorized to act as a landlord.

### Step 2. Create your backend listing files

```text
backend/app/
│
├── api/v1/endpoints/
│   └── listings.py
│
├── models/
│   └── listing.py
│
├── schemas/
│   └── listing.py
│
├── repositories/
│   └── listing_repository.py
│
└── services/
    └── listing_service.py
```

You don't need to write all these files simultaneously. Build them one by one.

Their responsibilities:

- `models/listing.py`: Defines the SQLAlchemy model.
- `schemas/listing.py`: Defines validated input and output structures.
- `repositories/listing_repository.py`: Retrieves and stores listing records.
- `services/listing_service.py`: Applies business rules.
- `api/v1/endpoints/listings.py`: Exposes the HTTP endpoints.

### Step 3. Add the first endpoints

Implement these in order:

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/listings` | Retrieve public listings |
| `GET /api/v1/listings/{listing_id}` | Retrieve one listing |
| `GET /api/v1/areas` | Retrieve available areas |

Initially, return only listings that are published, available, and approved for public display according to your moderation rules.

For the first milestone, you can insert a handful of test listings directly into Neon and use the API to retrieve them.

### Step 4. Build the frontend listing pages

Your first frontend branch should contain only the pages needed for browsing.

```text
frontend/src/
│
├── pages/
│   ├── ListingsPage.tsx
│   └── ListingDetailsPage.tsx
│
├── components/
│   ├── ListingCard.tsx
│   ├── ListingGrid.tsx
│   └── SearchFilters.tsx
│
├── services/
│   └── listingService.ts
│
└── types/
    └── listing.ts
```

The listing page fetches data from FastAPI and displays it.

A listing card could show:

- A photo.
- The monthly rent.
- The location.
- The room type.
- The availability date.
- A button to view details.

**Milestone:** A visitor can browse actual room listings retrieved from Neon through your backend.

At this point, you have the beginnings of a real product rather than just a database.

---

# Phase 4: Build authentication and user roles

**Branch:** `feature/authentication`

Once public browsing works, implement user registration and login.

### Features to build

1. User registration.
2. User login and logout.
3. Secure session or token handling.
4. User profile.
5. Role assignments.
6. Authorization checks.

Your database already has the basic identity model:

```text
users
  |
  | 1-to-many
  v
user_roles
  |
  | many-to-1
  v
roles
```

For the initial implementation, focus on tenants and landlords. Create the admin role in the database, but defer the full admin interface until moderation is ready.

### Suggested endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register` | Register a user |
| `POST /api/v1/auth/login` | Authenticate a user |
| `GET /api/v1/users/me` | Retrieve the authenticated user's profile |
| `PATCH /api/v1/users/me` | Update the user's profile |

Use a maintained authentication library or established security implementation. Do not invent your own password hashing, token validation, or session security.

### Security milestone

Verify that a tenant cannot access another tenant's profile or modify a listing they do not own.

This is more important than making the login page look attractive.

---

# Phase 5: Build the landlord dashboard

**Branch:** `feature/landlord-dashboard`

Now that authentication works, let landlords manage their listings.

### Features

- Create a listing.
- Edit a listing.
- Upload listing photos.
- Set availability.
- Withdraw a listing.
- View listing status.
- View contact requests.

### Suggested frontend structure

```text
frontend/src/features/landlord/
├── pages/
│   ├── LandlordDashboard.tsx
│   ├── CreateListingPage.tsx
│   └── EditListingPage.tsx
│
├── components/
│   ├── ListingForm.tsx
│   └── MyListingsTable.tsx
│
└── services/
    └── landlordService.ts
```

### Suggested backend endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/listings` | Create a listing |
| `PATCH /api/v1/listings/{id}` | Update an owned listing |
| `GET /api/v1/users/me/listings` | Retrieve the landlord's listings |
| `POST /api/v1/listings/{id}/submit` | Submit a listing for moderation |
| `POST /api/v1/listings/{id}/withdraw` | Withdraw an owned listing |

For photo uploads, use object storage rather than storing image files directly in PostgreSQL. Store the resulting file references in `listing_photos`.

**Milestone:** A landlord can register, log in, create a room listing, and see that listing in their dashboard.

---

# Phase 6: Build the tenant contact-request system

**Branch:** `feature/contact-requests`

Now let tenants express interest in a room.

### Features

- Submit a contact request.
- View personal contact requests.
- View request status.
- Allow landlords to respond.
- Approve or reject requests.
- Prevent unauthorized access to private contact details.

### Suggested endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/listings/{id}/contact-requests` | Submit a request |
| `GET /api/v1/users/me/contact-requests` | View the tenant's requests |
| `GET /api/v1/users/me/received-requests` | View requests received by a landlord |
| `PATCH /api/v1/contact-requests/{id}` | Update a permitted request status |

Your `contact_requests` table should have foreign keys to the listing and tenant.

You should also define the allowed status transitions, for example:

```text
pending
   |
   +----> approved
   |
   +----> rejected
   |
   +----> cancelled
```

The backend must check that the person changing the status is authorized to do so.

Don't allow a tenant to approve their own request or a landlord to approve requests for someone else's listing.

**Milestone:** A tenant can contact a landlord through the platform without the application exposing private contact information prematurely.

---

# Phase 7: Build moderation and reporting

**Branches:**
- `feature/listing-moderation`
- `feature/reporting`

These are separate features, so implement them independently.

## Listing moderation

An administrator needs to review listings before they become publicly available.

Build:

- A pending-listings dashboard.
- Listing approval and rejection.
- Moderation reasons.
- Moderation history.
- The ability to hide a published listing.

Your `listing_moderation` table should preserve previous decisions rather than overwriting the history.

Only an authenticated user with appropriate admin permissions should be able to moderate listings.

## Reporting

Allow tenants to report suspicious listings or inappropriate behavior.

Build:

- A report submission form.
- A report status page.
- An admin report queue.
- Report assignment.
- Report resolution and dismissal.

Your `reports` table should reference the reporting user and, where applicable, the listing or other resource being reported.

**Milestone:** Administrators can moderate listings and manage reports, with an auditable history of their actions.

---

# Phase 8: Build saved searches and reviews

**Branches:**
- `feature/saved-searches`
- `feature/reviews`

These features can be implemented after the main rental workflow works.

### Saved searches

Allow tenants to save search criteria such as:

- Preferred area.
- Maximum rent.
- Room type.
- Required amenities.

Initially, just save and retrieve these criteria.

Add automated notifications later.

### Reviews

Allow eligible tenants to review their rental experience.

Use the contact request to establish the relationship between the tenant and the listing. Enforce your eligibility rules on the backend so that users cannot review arbitrary listings.

**Milestone:** Tenants can save their preferences and submit eligible reviews.

---

# Phase 9: Add conversations and WhatsApp

**Branches:**
- `feature-web-conversations`
- `feature-whatsapp-integration`

I recommend building web-based conversations before integrating WhatsApp.

Your class diagram includes `Conversation`, `Message`, `ConversationService`, and `WhatsAppGateway`. These provide a useful starting point.

### First: web conversations

Implement:

- Conversation creation.
- Conversation participants.
- Message sending and retrieval.
- Message status tracking.
- Authorization checks for every conversation.

The database should enforce that a message belongs to a conversation and that its sender is an authorized participant.

### Next: WhatsApp

Once web conversations work, add the WhatsApp integration.

Implement:

1. Webhook verification.
2. Incoming-message processing.
3. Outgoing-message delivery.
4. Duplicate-event prevention.
5. Error handling and retries.
6. Message and conversation persistence.

Store incoming webhook events so that processing the same event twice does not create duplicate messages or repeat sensitive actions.

**Milestone:** Users can communicate through the website, and you have a clear path to supporting WhatsApp without duplicating your messaging logic.

---

# Phase 10: Introduce AI into the platform

**Branch:** `feature/ai-assistant`

Do not start by giving the LLM control over your database. Begin with one narrow, low-risk use case.

I suggest starting with **natural-language room search**.

A tenant might write:

> Find a furnished room near campus for less than R4,000 per month.

The AI interprets the request into structured criteria:

```json
{
  "location": "near campus",
  "max_monthly_rent": 4000,
  "furnished": true
}
```

Your backend validates those criteria and retrieves matching listings from PostgreSQL.

The AI should not invent room availability or claim a listing exists without retrieving it from the database.

### Build AI functionality in stages

| Stage | AI feature | Risk |
|---|---|---|
| 1 | Interpret natural-language searches | Relatively low |
| 2 | Extract listing details from landlord messages | Moderate |
| 3 | Draft listing descriptions for landlord review | Moderate |
| 4 | Assist with contact-request workflows | Higher |
| 5 | Perform authorized listing updates through tools | Higher |
| 6 | Automate selected WhatsApp workflows | Higher |

For actions that change records, the backend must independently verify the user's identity, ownership, permissions, and the requested state change.

For sensitive actions, such as approving access to personal contact information, require explicit confirmation or a human decision where appropriate.

### Suggested AI backend structure

```text
backend/app/
│
├── ai/
│   ├── assistant.py
│   ├── prompts.py
│   ├── schemas.py
│   └── tools.py
│
└── services/
    └── listing_service.py
```

The AI tools should call your existing business services rather than bypassing them.

For example:

```text
User's message
      |
      v
AI assistant
      |
      v
Structured search criteria
      |
      v
Listing service
      |
      v
PostgreSQL
      |
      v
Matching rooms
      |
      v
AI formats the results
```

This allows the same listing service to work for your website, WhatsApp bot, and future AI interfaces.

---

# 3. Your Copilot development workflow

Since Copilot will assist you, I recommend giving it small, specific tasks instead of asking it to build an entire phase.

## Create a project instruction file

Create:

`.github/copilot-instructions.md`

Use this as a starting point:

# Room Rental Platform — Development Instructions

## Project
Build a room rental platform where tenants can discover rooms, landlords can manage listings, and administrators can moderate content.

## Technology
- Frontend: React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, Pydantic
- Database: Neon PostgreSQL
- ORM: SQLAlchemy
- Migrations: Alembic
- Testing: Pytest
- Version control: Git and GitHub

## Architecture
- Keep frontend and backend code separate.
- Use API endpoints, services, repositories, database models, and schemas for their respective responsibilities.
- Keep business logic out of API endpoint handlers where practical.
- Use database migrations for schema changes.
- Follow the existing project structure and conventions.

## Security
- Never commit secrets or database credentials.
- Read configuration from environment variables.
- Validate all incoming data.
- Use parameterized database operations.
- Authenticate users and authorize every protected operation.
- Verify resource ownership before modifying or exposing private records.
- Never trust user IDs, roles, ownership claims, or permissions supplied by an LLM.
- Do not expose private contact information without authorization.
- Give AI tools access only to explicitly permitted application operations.

## Development workflow
- Implement one small feature at a time.
- Inspect existing code before making changes.
- Explain the planned changes before implementing them.
- Write tests for new functionality.
- Do not modify unrelated files.
- Do not silently change database schemas.
- Create Alembic migrations for database schema changes.
- Run relevant tests and explain their results.
- Document any assumptions or unresolved design decisions.

## Collaboration
- Explain unfamiliar code and architectural decisions.
- Ask before introducing major dependencies or changing the architecture.
- Prefer simple, maintainable solutions over unnecessary complexity.
- Do not claim that code or tests work without actually verifying them.

## Use this pattern for each Copilot task

Before asking Copilot to implement a feature, make sure you can answer four questions:

1. What is the feature supposed to do?
2. What data does it need?
3. What should the user be allowed to do?
4. How will you test that it works?

Then ask Copilot to implement only that feature.

For example, your first listing task could be:

Implement the first public-listings feature for the Room Rental Platform.

Before coding, inspect the existing project structure and explain the proposed changes.

Requirements:
1. Create a SQLAlchemy model for listings that matches the existing database design.
2. Create Pydantic schemas for listing responses.
3. Implement GET /api/v1/listings and GET /api/v1/listings/{listing_id}.
4. Return only listings that are eligible for public display.
5. Use the existing database session and repository/service structure.
6. Validate query parameters and handle missing listings appropriately.
7. Add automated tests for successful retrieval, filtering, and missing records.
8. Do not implement authentication, landlord CRUD operations, AI, or unrelated features yet.
9. Do not change the database schema without proposing an Alembic migration first.

After implementation, summarize the changed files, explain the code, and report which tests were actually run and their results.

You should still review the generated code yourself. Copilot can produce plausible code that has incorrect assumptions, missing authorization checks, or queries that don't match your actual schema.

---

# 4. Use a definition of done for every feature

Before merging a feature into `develop`, check the following.

| Check | Question |
|---|---|
| Functionality | Does the feature perform the intended task? |
| Database | Does it use the correct tables and relationships? |
| Validation | Does it reject invalid input? |
| Security | Can users access only permitted records and actions? |
| Testing | Have the relevant tests passed? |
| Documentation | Are important assumptions and API changes documented? |
| Git | Has the feature been committed on its own branch? |

Not every feature needs a complex test suite at the beginning. However, authorization, contact privacy, and AI-triggered actions deserve particular attention.

---

# 5. Your first four weeks: a suggested schedule

This is a suggested sequence, not a fixed deadline.

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Project setup, Neon connection, initial migrations | Working FastAPI application connected to Neon |
| 2 | Public listing API and basic frontend | Visitors can browse rooms |
| 3 | Authentication and landlord dashboard | Landlords can create and manage their own listings |
| 4 | Contact requests and initial authorization checks | Tenants can contact landlords securely |

After that, continue with moderation, reporting, reviews, saved searches, conversations, WhatsApp, and AI.

The timeline may change depending on your experience and the amount of time you have available.

---

# 6. What I recommend you do right now

Don't start implementing all ten phases.

Start with this small checklist:

- [ ] Create the GitHub repository.
- [ ] Create `main` and `develop` branches.
- [ ] Create the initial folder structure.
- [ ] Add `.gitignore` and `.env.example`.
- [ ] Create the Copilot instruction file.
- [ ] Set up FastAPI.
- [ ] Connect FastAPI to Neon.
- [ ] Create and test the `/health` endpoint.

Once those steps work, create your first feature branch for public room listings.

**One final recommendation:** Keep your ERD as the source of truth for database relationships, your class diagram as a guide to application responsibilities, and your API documentation as the contract between the frontend and backend. They serve different purposes, and keeping them aligned will make the project much easier to maintain.

If you follow this incremental approach, you'll end up with a platform that works at every stage, rather than a large collection of code that is difficult to test or debug.