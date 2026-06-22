# IAM 3.0 — Implementation Plan by Phase

**System 19 — Centralised Identity, Authentication, Authorisation & Access-Control Platform**
**Greenfield build | Zitadel IdP + Django Backend | CLET/GSL**

---

## Phase Overview

| Phase | Focus | Duration (est.) | Depends On |
|-------|-------|-----------------|------------|
| Sprint 0 | Foundation, infra, tooling, models | 2–3 weeks | — |
| Phase 1 | Core identity, SSO, Custom Login UI, Admin Console | 8–10 weeks | Sprint 0 |
| Phase 2 | Lifecycle automation, self-service, resilience | 4–6 weeks | Phase 1 |
| Phase 3 | Delegation, PAM, access-review rhythm | 4–6 weeks | Phase 1 |

---

## Sprint 0 — Foundation Lock-In & Base Infrastructure

**Goal:** Standing infrastructure, project skeleton, shared models, CI/CD, and Zitadel cluster ready for Phase 1 development.

### 0.1 Zitadel Cluster Bring-Up

- [ ] **0.1.1** Deploy Zitadel Helm chart on K8s (3+ replicas, production spec)
  - Choose Zitadel version and lock it (e.g. Zitadel v2.x stable)
  - Configure PostgreSQL with synchronous streaming replication (RPO 0)
  - Deploy Redis for Zitadel session cache
  - Configure ingress with TLS 1.3
  - Document cluster topology
- [ ] **0.1.2** Configure Zitadel organization & project
  - Create organisation (`clet-ghana`)
  - Create IAM project (`iam-system-19`)
  - Register Custom Login UI URLs (Django endpoints — stub them in Sprint 0)
  - Disable Implicit + ROPC grants at project level
  - Require PKCE S256 for all public clients
  - Enable client credentials grant (S2S)
- [ ] **0.1.3** Create Zitadel service account for Management API
  - Generate signed JWT, store in Vault
  - Grant appropriate scoped roles (`IAM_OWNER`)
- [ ] **0.1.4** Verify Zitadel OIDC endpoints
  - Discovery, JWKS, authorize, token, userinfo, introspect, revoke
  - Test PKCE S256 auth code flow manually

### 0.2 Django Project Skeleton

- [ ] **0.2.1** Initialize Django project (`config/`)
  - Python 3.12+, `uv` package manager
  - Split settings: `base.py`, `dev.py`, `staging.py`, `prod.py`
  - `uv` for dependency management
- [ ] **0.2.2** Create core shared app (`core/`)
  - `exceptions.py` — unified DRF exception handler + envelope
  - `middleware.py` — correlation ID, security headers, signed-header validation
  - `risk.py` — IP geo, ASN, known-bad-IP, device fingerprint interfaces
  - Base models: `UUIDModel`, `TimestampedModel`
- [ ] **0.2.3** Create `accounts/` app — custom `User` model
  - `AUTH_USER_MODEL = accounts.User`
  - Fields: `id (UUIDField, PK)`, `zitadel_user_id (UUIDField, unique, indexed)`, `email`, `phone`
  - **No `password` field** — credentials live in Zitadel
  - `user_type` (`staff|board|nbec|student|external|public`)
  - `status` (`pre_active|active|disabled|pending`)
  - `metadata` JSONB field with user-type-specific schemas
  - `created_at`, `last_login_at`, `hrms_event_ref`
  - Register first migration
- [ ] **0.2.4** Create remaining model stubs (no migrations yet)
  - `ZitadelUserSync`, `OIDCClient`, `Role`, `RoleBinding`, `RoleClaim`
  - `Delegation`, `PamSession`, `AccessReviewCampaign`
  - `AuditEvent`, `ActiveSession`, `RuleDefinition`
  - *Models are defined; migrations created when the app is implemented*
- [ ] **0.2.5** Configure DRF, `mozilla-django-oidc`, Celery, Celery Beat
  - DRF: unified envelope renderer, auth classes (Bearer via JWKS)
  - `mozilla-django-oidc`: Zitadel JWKS validation, claim mapping stubs
  - Celery + Redis broker config
  - Celery Beat schedule placeholder

### 0.3 DevOps & Tooling

- [ ] **0.3.1** Set up `Dockerfile` + `docker-compose.yml` (dev)
  - Django container, PostgreSQL, Redis, Celery worker
- [ ] **0.3.2** CI/CD pipeline (GitHub Actions / GitLab CI)
  - `lint` — ruff, mypy (strict mode)
  - `test` — `pytest` with `--cov`, split into unit/api/integration/security
  - `security` — `bandit`, `pip-audit` (or `uv audit`)
  - `docker` — build + push image
  - `deploy` — manual trigger for staging
- [ ] **0.3.3** Terraform skeleton (`infra/terraform/`)
  - K8s namespace, service account, network policies
  - Vault configuration for secrets
  - PostgreSQL (Django), Redis, Zitadel Helm values
- [ ] **0.3.4** K8s manifests (`infra/k8s/`)
  - Django Deployment + Service + Ingress
  - Celery worker Deployment
  - ConfigMap for non-sensitive settings
  - Secret template (Vault sidecar or external-secrets)
- [ ] **0.3.5** Dev environment
  - Local Zitadel instance (docker-compose) or shared dev Zitadel
  - `.env.example` with documented variables
  - `Makefile` for common commands

### 0.4 Governance & Docs

- [ ] **0.4.1** Record `DEV-IAM-01-R` (IdP decision reversal)
- [ ] **0.4.2** Sign off Sprint 0 deliverables and Phase 1 backlog
- [ ] **0.4.3** Set up test directories: `tests/unit/`, `tests/api/`, `tests/integration/`, `tests/security/`

### Sprint 0 Deliverables
- Zitadel cluster running and verified
- Django project skeleton with custom User model
- CI/CD green on `main`
- Docker Compose dev environment
- All model classes defined
- Test framework wired

---

## Phase 1 — Core Identity Substrate & SSO with Custom Login UI

**Goal:** Users can authenticate via Zitadel through a branded Django Custom Login UI, admins can manage users/roles/clients via the Admin Console API, and all actions are audit-chained.

### 1.1 Zitadel OIDC Provider Verification

- [ ] **1.1.1** Verify full OIDC protocol against Zitadel
  - Discovery document, JWKS endpoint, token endpoint, userinfo, introspect, revoke
  - PKCE S256 enforcement test
  - `client_credentials` grant test (S2S)
  - Confirm Implicit + password grants are rejected (403)
- [ ] **1.1.2** Create Admin Console OIDC client in Zitadel
  - Confidential client, Auth Code + PKCE
  - Configure redirect URIs, post-logout redirect URIs
  - Enable back-channel logout
- [ ] **1.1.3** Verify Zitadel Auth API + Management API access
  - Test service account JWT authentication
  - Test `/auth/v1/users/{id}/verify_password`
  - Test MFA challenge/verification endpoints
  - Test consent API
  - Document exact request/response contracts

### 1.2 Django `login/` App — Custom Login UI

- [ ] **1.2.1** Build Zitadel Auth API service layer (`login/zitadel_auth.py`)
  - `authenticate_user(email, password)` → calls verify_password API
  - `create_zitadel_session(user_id)` → returns session token
  - `verify_mfa_factor(session_id, factor_type, code)`
  - `grant_consent(auth_request_id)`
  - `trigger_password_reset(email)`
  - All with retry, timeout, error mapping
- [ ] **1.2.2** Build login flow endpoints
  - `GET /login?authRequest=...` — branded login form
  - `POST /login` — authenticate via Zitadel, create session, redirect
  - `GET /mfa/{factor}?authRequest=...` — TOTP/WebAuthn/SMS forms
  - `POST /mfa/{factor}` — verify via Zitadel Auth API
  - `GET /consent?authRequest=...` — consent screen
  - `POST /consent` — approve/deny via Zitadel API
  - `GET /password-reset` — reset form
  - `POST /password-reset` — trigger Zitadel reset
  - `GET /error?error=...&error_description=...` — error page
- [ ] **1.2.3** Build Django templates (`login/templates/login/`)
  - Branded, accessible (WCAG 2.1 AA)
  - HTMX for dynamic interactions
  - Error states for every form
  - Loading/disabled states for async calls
- [ ] **1.2.4** Build risk evaluator (`login/risk.py`)
  - Device fingerprint collection (JS)
  - IP geo + ASN lookup
  - Known-bad-IP check
  - Time-of-day anomaly
  - Risk score → `acr` step-up signal
- [ ] **1.2.5** Wire up end-to-end login flow
  - User → RP → Zitadel → Django login → Zitadel Auth API → MFA → Consent → Code → Token
  - Test with a sample RP (in dev)

### 1.3 Django `oidc_rp/` App — Relying Party for Admin Console

- [ ] **1.3.1** Configure `mozilla-django-oidc`
  - `OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET` (from Zitadel Admin Console client)
  - `OIDC_OP_JWKS_ENDPOINT` — Zitadel JWKS
  - `OIDC_OP_AUTHORIZATION_ENDPOINT`, `OIDC_OP_TOKEN_ENDPOINT`, `OIDC_OP_USERINFO_ENDPOINT`
  - `OIDC_OP_LOGOUT_ENDPOINT` — RP-Initiated Logout
- [ ] **1.3.2** Custom claim mapping
  - `sub → user.zitadel_user_id`
  - `email → user.email`
  - `user_type`, `roles[]`, `portal_access[]`, `permissions[]` from Zitadel metadata/claims
  - `OIDC_AUTHENTICATION_CALLBACK` — create/update local Django `User` on first login
- [ ] **1.3.3** Token validation
  - Verify against Zitadel JWKS
  - Check `iss`, `aud`, `exp`, `nbf`, `iat`, `kid`
  - `nonce` + `state` enforcement
- [ ] **1.3.4** Back-channel logout endpoint
  - `POST /backchannel-logout`
  - Validate logout token (Zitadel-signed)
  - Invalidate local `ActiveSession` records
- [ ] **1.3.5** Session management
  - `ActiveSession` CRUD (create on login, revoke on logout)
  - Session list API for self-service
  - Idle timeout enforcement (optional — Zitadel handles SSO timeout)

### 1.4 Django `accounts/` App — Full User Management

- [ ] **1.4.1** User admin (Django Admin + DRF APIView)
  - List, detail, create, update, deactivate
  - Bulk import (CSV with validation, row-level error report)
  - **Write path:** create/update in Zitadel (via Management API) + create/update in Django
  - **Read path:** Django DB (source of truth for business metadata)
- [ ] **1.4.2** Invite flow
  - Admin creates user → triggers Zitadel user creation → sends invite email
  - Invite link (single-use, 24-h validity) → Custom Login UI → password set
  - User status: `pre_active → active` after first login

### 1.5 Django `console/` App — Admin Console API

- [ ] **1.5.1** Users endpoint (`/v1/admin/users`)
  - `GET /v1/admin/users` — paginated list (search, filter by `user_type`/`status`)
  - `POST /v1/admin/users` — create (dual-write Zitadel + Django)
  - `GET /v1/admin/users/{id}` — detail
  - `PATCH /v1/admin/users/{id}` — update metadata
  - `DELETE /v1/admin/users/{id}` — deactivate (disable in Zitadel, set status)
  - `POST /v1/admin/users/bulk-import` — CSV with row-level report
- [ ] **1.5.2** Roles endpoint (`/v1/admin/roles`)
  - `GET /v1/admin/roles` — catalogue list (per system, versioned)
  - `POST /v1/admin/roles` — create role definition
  - `GET /v1/admin/roles/{id}` — role detail with permission strings
  - `PATCH /v1/admin/roles/{id}` — update (version bump)
  - `POST /v1/admin/roles/{id}/bind` — assign role to user (requires DG approval for elevated)
  - `POST /v1/admin/roles/{id}/unbind` — revoke role
- [ ] **1.5.3** Clients endpoint (`/v1/admin/clients`)
  - `GET /v1/admin/clients` — list OIDC clients
  - `POST /v1/admin/clients` — register new client (wraps Zitadel project/app API)
  - `GET /v1/admin/clients/{id}` — detail
  - `POST /v1/admin/clients/{id}/promote` — sandbox → production
  - `POST /v1/admin/clients/{id}/rotate-secret` — trigger secret rotation
- [ ] **1.5.4** Audit endpoint (`/v1/admin/audit`)
  - `GET /v1/admin/audit` — search audit events (date range, actor, action, entity)
  - `GET /v1/admin/audit/export` — signed PDF+JSON export
- [ ] **1.5.5** Permission enforcement
  - Decorators/classes for: `require_role('iam-admin')`, `require_role('dg')`, etc.
  - SoD check: IAM-Admin + Internal-Auditor on same account → `ROLE_CONFLICT`
  - Step-up required for elevated actions (force re-auth with MFA)

### 1.6 RBAC Role Catalogue & Zitadel Claims Push

- [ ] **1.6.1** Role model + role-binding lifecycle
  - Request → DG approval → effective → revoked
  - Versioned catalogue (per system, permission strings)
- [ ] **1.6.2** Role → Zitadel claim mapping (`RoleClaim`)
  - When role binding is created/updated/revoked, update Zitadel user metadata
  - Ensure next issued token carries updated `roles[]`, `permissions[]` claims
  - Retry logic for Zitadel API failures
- [ ] **1.6.3** Separation-of-duties rules
  - `RuleDefinition` model with JSON predicates
  - Evaluate before binding; reject with `ROLE_CONFLICT` + audit log

### 1.7 Django `audit/` App — Audit Chain Manager

- [ ] **1.7.1** `AuditEvent` model + emission API
  - `emit_event(actor, action, entity_type, entity_id, metadata, channel, result, ...)`
  - Append-only (logical deletes only)
  - Retention: 10 years (SRS §7)
- [ ] **1.7.2** Hash chain
  - `hash_chain_ref = SHA256(prev_hash ‖ canonical_event_json)`
  - Last hash persisted in DB and sent to System 22
  - Nightly Celery Beat job: rebuild chain from last known anchor, verify
- [ ] **1.7.3** Event capture points
  - Login success/failure (from Custom Login UI)
  - Console actions (user/role/client CRUD)
  - SCIM operations (onboard/mover/leaver)
  - Delegation grant/expiry/revoke
  - PAM session lifecycle
  - Access-review decisions
- [ ] **1.7.4** Zitadel event integration
  - Option A: Zitadel webhook → Django endpoint → emit audit event
  - Option B: Django-side interception (every Custom Login UI interaction emits)
  - Option C: Zitadel Management API event polling (fallback)
- [ ] **1.7.5** System 22 forwarder
  - Outbox table: undelivered events with retry
  - Celery Beat: flush outbox → POST to System 22 → mark sent
  - Idempotency key per event

### 1.8 Django `lifecycle/` App — SCIM 2.0 Listener & HRMS Stub

- [ ] **1.8.1** SCIM 2.0 endpoints (`/scim/v2/Users`)
  - `POST /scim/v2/Users` — onboard (create Zitadel user + Django record)
  - `PATCH /scim/v2/Users/{id}` — mover (update metadata)
  - `DELETE /scim/v2/Users/{id}` — leaver (disable Zitadel user, terminate sessions)
  - `GET /scim/v2/Users/{id}` — query
  - `GET /scim/v2/Users` — search
- [ ] **1.8.2** SCIM → Zitadel dual-write abstraction
  - Interface: `UserProvisionerBackend`
  - Zitadel Management API implementation
  - Fallback: Zitadel SCIM endpoint if available
- [ ] **1.8.3** HRMS webhook stub (Phase 1 placeholder)
  - Accept signed webhook events (joiner/mover/leaver)
  - Validate HMAC signature
  - Queue Celery task for processing
- [ ] **1.8.4** Cleanup jobs
  - Celery Beat: purge unverified accounts (status `pending`, age > 7 days)
  - Celery Beat: sync Zitadel user status → Django status

### 1.9 Compliance Gate

- [ ] **1.9.1** Per-RP compliance checklist
  - No parallel password store at the RP
  - PKCE S256 enforced
  - Implicit + password grants disabled
  - Token validation against Zitadel JWKS
  - Back-channel logout implemented
- [ ] **1.9.2** Sandbox → production promotion gate
  - Green sandbox tests
  - Compliance gate passed
  - IAM-Admin approval

### 1.10 Phase 1 Demo

- [ ] **1.10.1** End-to-end walkthrough
  1. Admin creates staff user via Admin Console API
  2. Zitadel user created → invite email sent
  3. User clicks invite → password set via Custom Login UI
  4. User logs in → MFA challenge → consent → auth code → token
  5. SSO into sandbox RP (token validated against Zitadel JWKS)
  6. Admin assigns elevated role → DG approval → role binding effective
  7. User's next token carries new roles
  8. All actions visible in audit chain
  9. Signed audit export verified

### Phase 1 Deliverables
- Custom Login UI: login, MFA (TOTP/WebAuthn/SMS), consent, password reset, error screens
- OIDC RP flow: Admin Console authenticated via Zitadel
- Admin Console API: users, roles, clients, audit CRUD
- Role catalogue + Zitadel claims push
- Audit Chain Manager with SHA-256 chaining
- SCIM 2.0 listener with dual-write to Zitadel
- Compliance gate for RPs

---

## Phase 2 — Lifecycle Automation, Self-Service & Resilience

**Goal:** Fully automated user lifecycle from HRMS, self-service registration for non-staff users, logout propagation, and DR readiness.

### 2.1 HRMS SCIM 2.0 Integration

- [ ] **2.1.1** Real HRMS SCIM 2.0 connection
  - Cut over from stub to real System 09 SCIM endpoint
  - Verify SLAs: joiner ≤ 1 h, mover ≤ 1 h, leaver disable ≤ 4 h
- [ ] **2.1.2** Leaver flow automation
  - HRMS leaver event → disable Zitadel user → terminate all active sessions (≤ 60 s)
  - Update Django `User.status = disabled`
  - Emit audit event
  - Propagate door-access revocation (S160a) via System 22 event
- [ ] **2.1.3** Mover flow
  - Update Zitadel user metadata
  - Update Django `User.metadata` (department, line manager, etc.)
  - Re-evaluate role bindings (new department may change eligibility)
- [ ] **2.1.4** Joiner flow
  - Create Zitadel user + Django record
  - Assign default role (lowest-privilege for `user_type`)
  - Send invite email

### 2.2 Self-Service Registration

- [ ] **2.2.1** Registration flow (student/external/public)
  - `GET /register` — branded registration form
  - `POST /register` — validates email, creates `pre_active` user in Django
  - Email verification: sends verification link (single-use, 24-h validity)
  - `GET /verify-email?token=...` — verifies → creates in Zitadel → status `active`
  - Rate limiting: N registrations per IP per hour
  - Captcha (reCAPTCHA or hCaptcha)
  - Anomaly detection (known-spam domains, rapid-fire registration)
- [ ] **2.2.2** Unverified account cleanup
  - Celery Beat: purge accounts older than 7 days with status `pending`
  - Remove from Django DB + Zitadel (via Management API)

### 2.3 RP-Initiated Logout & Back-Channel Logout

- [ ] **2.3.1** RP-Initiated Logout
  - `GET /logout` → `end_session` endpoint with `id_token_hint`
  - Redirect to Zitadel logout → Zitadel terminates SSO session
  - Zitadel emits back-channel logout tokens to all RPs
- [ ] **2.3.2** Back-channel logout delivery SLA
  - Zitadel emits → Django receives → invalidates local sessions ≤ 30 s
  - Verify all RPs receive and process logout tokens

### 2.4 DR Resilience

- [ ] **2.4.1** Quarterly DR drill
  - Zitadel HA failover test (active → standby)
  - Django stateless scale-out test (add pods, verify zero auth failures)
  - 15-min RTO validation
- [ ] **2.4.2** Restore drill (monthly)
  - Restore Django DB from backup
  - Verify audit chain integrity post-restore

### 2.5 Mandatory Student MFA Rollout

- [ ] **2.5.1** Zitadel policy toggle
  - Enable MFA requirement for `student` user type
  - Configure allowed factors (TOTP + SMS, no WebAuthn-only)
- [ ] **2.5.2** Communications campaign
  - Notify students of upcoming MFA requirement
  - Provide setup instructions via self-service

### Phase 2 Deliverables
- HRMS SCIM integration: automated joiner/mover/leaver
- Self-service registration with email verification
- RP-Initiated Logout + back-channel logout ≤ 30 s
- Quarterly DR drill proven
- Mandatory student MFA enabled

---

## Phase 3 — Delegation, PAM & Access-Review Rhythm

**Goal:** Governance Portal integration for delegation, PAM session management with audit anchoring, and quarterly access-review campaigns.

### 3.1 Delegation (`delegation/` App)

- [ ] **3.1.1** Governance Portal webhook ingress
  - Validate HMAC-SHA256 signature
  - Parse delegation grant/revoke events
  - Queue Celery task for processing
- [ ] **3.1.2** Delegation lifecycle
  - `POST /delegation/webhook` — receive event → create `Delegation` record
  - Auto-grant role binding (≤ 60 s from receipt)
  - Push role claims to Zitadel (update user metadata)
  - Start TTL timer
- [ ] **3.1.3** Delegation expiry
  - Celery Beat: per-minute check for expired delegations
  - On expiry: revoke role binding in Django + update Zitadel user claims
  - Terminate Zitadel sessions for affected user
  - Emit audit event
- [ ] **3.1.4** Revocation
  - Governance Portal sends revoke webhook
  - Remove role binding immediately
  - Update Zitadel claims
  - Terminate sessions

### 3.2 PAM (`pam/` App)

- [ ] **3.2.1** JumpServer + Vault integration
  - Short-lived credential issuance via Vault
  - JumpServer session recording (video + keystroke)
  - WORM storage for recordings
- [ ] **3.2.2** PAM session lifecycle
  - `PamSession` model: user, target, start/end time, recording URI, recording SHA-256
  - Session start → create `PamSession` → anchor to audit chain
  - Session end → finalize recording → anchor SHA-256 to System 22
- [ ] **3.2.3** Retention & audit
  - 7-year retention (SRS §7)
  - Daily SHA-256 anchoring to audit chain
  - Auditor read-only access with tamper detection

### 3.3 Access-Review Campaigns

- [ ] **3.3.1** Campaign model
  - `AccessReviewCampaign`: period, scope, reviewer, decision count, completed at
  - Quarterly schedule (Celery Beat)
- [ ] **3.3.2** Review workflow
  - Generate list of role bindings in scope
  - Assign to reviewer (DG or IAM-Admin)
  - Reviewer decides: keep / revoke / change role
  - Revocations take effect within 5 business days
- [ ] **3.3.3** Reports
  - Signed report exportable to Auditor-General
  - Role-mining recommendations (optional, future)

### Phase 3 Deliverables
- Governance Portal delegation integration: auto-grant, TTL tracking, auto-expiry
- PAM session recording with SHA-256 audit anchoring
- Quarterly access-review campaigns with signed reports
- All session changes propagate to Zitadel within 60 s

---

## Future / Post-Phase 3

- Cross-system role-mining and SoD analytics
- Advanced risk scoring with ML models
- FIDO2 passkey-only mode for high-security roles
- Zitadel v3 migration (when stable)
- Real System 21 (Communications) integration replacing stubs
- Real System 22 (CALS) integration replacing stubs
- Real System 11 (Governance Portal) integration replacing stubs

---

## Dependency Graph

```
Sprint 0 ─────────────────────────────────────────────────────────────
    │
    ▼
Phase 1 ──────────────────────────────────────────────────────────────
    │
    ├── 1.1 Zitadel OIDC Verification ───┐
    ├── 1.2 Custom Login UI ─────────────┤
    ├── 1.3 oidc_rp App ─────────────────┤
    ├── 1.4 accounts App ────────────────┤
    ├── 1.5 console App ─────────────────┤
    ├── 1.6 RBAC ────────────────────────┤
    ├── 1.7 audit App ───────────────────┤
    ├── 1.8 lifecycle App ───────────────┤
    └── 1.9 Compliance Gate ─────────────┘
    │
    ▼
Phase 2 ──────────────────────────────────────────────────────────────
    │
    ├── 2.1 HRMS SCIM Integration ─────── (depends on 1.8)
    ├── 2.2 Self-Service Registration ─── (depends on 1.2, 1.4)
    ├── 2.3 Logout Propagation ────────── (depends on 1.3)
    ├── 2.4 DR Resilience ─────────────── (depends on 1.1)
    └── 2.5 Mandatory Student MFA ─────── (depends on 1.2, 1.7)
    │
    ▼
Phase 3 ──────────────────────────────────────────────────────────────
    │
    ├── 3.1 Delegation ────────────────── (depends on 1.6)
    ├── 3.2 PAM ───────────────────────── (depends on 1.7)
    └── 3.3 Access-Review ─────────────── (depends on 1.6)
```

## Key Principles

1. **Zitadel owns the IdP substrate** — Django never stores passwords, MFA secrets, or auth codes. All credential operations go through Zitadel's APIs.
2. **Django owns the business logic** — RBAC, audit chain, delegation, PAM records, local user metadata.
3. **Dual-write discipline** — Everything that affects users/clients/roles goes to both Zitadel and Django. Django is the source of truth for business metadata; Zitadel is the source of truth for credentials and tokens.
4. **Audit everything** — Every action that affects security or access generates an `AuditEvent`. The hash chain is non-negotiable.
5. **Phase 1 is the hard part** — Once the Custom Login UI, OIDC RP, Admin Console, and audit chain are working, Phase 2 and 3 add automation on top of a stable base.
6. **Stubs → cutover** — External systems (HRMS, Governance Portal, Communications, CALS) start as stubs in Phase 1 and cut over to real integrations in later phases.
