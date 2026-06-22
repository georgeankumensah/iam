---
name: iam-zitadel-backend
description: "Greenfield backend build blueprint for the CLET/GSL IAM System (System 19) with Zitadel as the external OpenID Connect provider and Django as the resource server, admin console, SCIM gateway, audit chain manager, and Custom Login UI host. Use whenever planning or implementing backend work in the iam-3.0 Django repository. Source of truth is the IAM SRS v1.0 (May 2026); covers the IdP decision reversal, system overview, Django apps, phases, data model, API, RBAC, MFA, audit, integrations, validation, testing, and implementation order."
metadata:
  author: team
  version: "1.0.0"
---

# IAM-3.0 Backend Blueprint — Zitadel IdP + Django Backend

Use this skill whenever planning or implementing backend work in the **`iam-3.0`** Django
repository. This repo is a **greenfield rebuild** of System 19 — nothing exists yet except the
project root. Build from this blueprint; do not assume any prior code.

**Source of truth:** the **IAM SRS v1.0, May 2026** (`Identity & Access Management (IAM)
Requirements.pdf`) — *System 19; Centralised Identity, Authentication, Authorisation and
Access-Control Platform*, Legislative Basis §§11, 12(3), 14(2), 16(2) of the Legal Education Act,
2026. Supporting sources: the **Volume II IAM Implementation Report**, the **System 17 (API &
Integration Layer) SRS**, and the **System 22 (Cybersecurity, Audit & Logging / CALS) SRS** for
the integration boundaries.

Every functional requirement below is traceable to a `SRS-IAM-Fxx` / `IAM-Nxx` / `REQ-F000` ID.
Do not implement behaviour that contradicts the SRS without a recorded deviation (`DEV-IAM-xx`).

---

## 0. IdP Decision: Zitadel IS the OpenID Connect Provider (`DEV-IAM-01-R`)

**This project reverses `DEV-IAM-01` from the earlier blueprint.** Zitadel is the external OpenID
Connect provider — it issues ID/Access tokens, owns the JWKS, manages OAuth clients and their
secrets, stores credentials, enforces MFA policies, rotates signing keys, handles refresh-token
rotation and family revocation, manages sessions, and emits back-channel logout tokens.

**`DEV-IAM-01-R`** — recorded deviation reversal: the earlier `DEV-IAM-01` (Django-native OIDC
provider) is rescinded. The SRS-named approach of using a COTS IdP (Zitadel) is adopted. Every
functional requirement still holds in full — only the implementation substrate changes from a
Django-native provider to Zitadel + Django.

**Two responsibilities stay in Django:**
1. **Custom Login UI** — Zitadel delegates all user-facing auth pages (login, MFA challenge,
   consent, password reset, error screens) to Django. Django calls Zitadel's Auth API server-side
   — credentials and MFA secrets never touch the Django database.
2. **Business backend** — Admin Console, SCIM provisioning, audit chain, RBAC catalogue,
   delegation, PAM records.

### What Zitadel provides out of the box (SRS §13 cost savings)

| Requirement | Handled By |
|---|---|
| Signing-key management + HSM / KMS integration (IAM-N09) | Zitadel (K8s or cloud KMS) |
| JWKS publication + RS256 rotation with overlap | Zitadel |
| OIDC Authorization Code + PKCE S256 (IAM-F01, IAM-N03) | Zitadel (configured per app) |
| Implicit & ROPC grant disabled | Zitadel (hard-disabled per project) |
| Refresh-token rotation + family revocation + replay detection (IAM-N02) | Zitadel |
| WebAuthn/passkeys + TOTP + SMS MFA (IAM-F02) | Zitadel (policy-based per org/project) |
| Forced MFA enrolment + recovery codes + factor lockout | Zitadel |
| Back-channel logout (RFC 7800 logout tokens) (IAM-F09) | Zitadel |
| Brute-force protection + rate limiting | Zitadel |
| Session management (idle/absolute timeouts) | Zitadel |
| RP-Initiated Logout (`end_session` + `id_token_hint`) | Zitadel |
| OIDC Discovery + userinfo + introspection + revocation | Zitadel |
| Client credentials grant (S2S, `client_credentials`) | Zitadel (per app) |
| SCIM 2.0 user provisioning (IAM-F06) | Zitadel SCIM endpoint or DNS API |

### What Django still builds (the remaining SRS surface)

| Requirement | Handled By |
|---|---|
| Custom Login UI (branded auth screens) | Django `login/` app |
| Admin Console API (`/v1/admin/*`) | Django `console/` app |
| RBAC role catalogue + role-binding lifecycle (IAM-F03) | Django `rbac/` app |
| Delegation TTL tracking + auto-expiry (IAM-F04) | Django `delegation/` app |
| PAM session records + recording hash anchoring (IAM-F05) | Django `pam/` app |
| Audit Chain Manager (SHA-256 chain, System 22 forwarder) (IAM-N04) | Django `audit/` app |
| SCIM 2.0 ingress + HRMS event handling (IAM-F06) | Django `lifecycle/` app |
| OIDC client lifecycle management (via Zitadel API) | Django `clients/` app |
| Risk-based step-up signals (acr/amr) (IAM-F02-03) | Django `login/` risk scorer |
| Self-service profile API (`/v1/me*`) | Django `console/` app |

---

## 1. Architecture Overview

System 19 is a self-hosted, cloud-native, Kubernetes-deployed identity platform that every other
CLET system depends on for access decisions. The platform consists of:

- **Zitadel (the IdP)** — K8s-deployed Zitadel cluster with PostgreSQL backend. Serves OIDC
  protocol endpoints, JWKS, token issuance, MFA, sessions, back-channel logout. Configured with
  Custom Login UI pointing at Django for all user-facing screens.
- **Django (Resource Server + Custom Login UI)** — DRF-based backend that serves:
  - `login/` — Zitadel Custom Login UI endpoints (login, MFA, consent, password reset, error)
  - `admin-console-api/` — `/v1/admin/*` for RBAC, clients, users, audit
  - `scim-listener/` — SCIM 2.0 ingress (`/scim/v2/Users`)
  - `audit-service/` — SHA-256 hash chain + System 22 forwarder
  - `self-service/` — `/v1/me*` profile + session management
- **PostgreSQL** for Zitadel (IdP state) + separate PostgreSQL for Django (business state),
  both with synchronous streaming replication (RPO 0, RTO 15 min — IAM-N01)
- **Redis** — Zitadel session cache + Django cache/Celery broker
- **HashiCorp Vault** — Django secrets, Zitadel admin service account keys
- **Celery + Celery Beat** — delegation expiry, audit-forward outbox, nightly chain validation
- **JumpServer + Vault** — PAM (unchanged from blueprint)
- **HTMX / vanilla JS** — for Zitadel Custom Login UI pages (lightweight, no SPA)
- **Prometheus + Grafana + Loki + OpenTelemetry** — metrics, dashboards, logs, traces

Phase 1 ships **stubs** for HRMS (09), Governance Portal (11), Communications (21), Audit &
Logging (22). Cutover to the real systems is configuration, not code.

---

## 2. Django App / Module Breakdown

Greenfield layout under the existing `config/` project.

- **`accounts/`** — custom user model (`AUTH_USER_MODEL = accounts.User`): **no password field**
  (credentials live in Zitadel), `zitadel_user_id` (UUID, unique, indexed), `email`, `phone`,
  `user_type` (`staff|board|nbec|student|external|public`), `status`
  (`pre_active|active|disabled|pending`), `metadata` JSONB, `created_at`, `last_login_at`,
  `hrms_event_ref`. This is a local mirror of Zitadel users for Django's business logic.
- **`login/`** — **Zitadel Custom Login UI**. Endpoints that Zitadel redirects to during the
  auth flow:
  - `GET /login` — login form (username + password)
  - `POST /login` — authenticates via Zitadel Auth API (`/auth/v1/users/{id}/verify_password`),
    creates Zitadel session, redirects back to Zitadel
  - `GET /mfa/{factor}` — TOTP/WebAuthn/SMS challenge form
  - `POST /mfa/{factor}` — verifies via Zitadel Auth API, continues flow
  - `GET /consent` — OIDC consent screen
  - `POST /consent` — grants/denies consent via Zitadel API
  - `GET /password-reset` — password reset form
  - `POST /password-reset` — calls Zitadel Management API to trigger reset
  - `GET /error` — auth error display page
  - Templates in `login/templates/login/` (branded, accessible)
  - Service layer in `login/zitadel_auth.py` wrapping Zitadel Auth + Management APIs
  - Risk evaluator in `login/risk.py` (device fingerprint, IP geo, ASN, known-bad-IP)
- **`oidc_rp/`** — Django acting as an OIDC Relying Party for its own Admin Console + self-service
  portal. Uses `mozilla-django-oidc` for the RP flow. Token validation against Zitadel JWKS.
  Custom claim mapping (`user_type`, `roles[]`, `portal_access[]`, `permissions[]`).
  Back-channel logout listener endpoint (`/backchannel-logout`).
- **`clients/`** — OIDC client lifecycle management via Zitadel Management API (gRPC or REST).
  Wraps Zitadel's project/app CRUD: Onboarding → Sandbox Validated → Production Live →
  Suspended → Decommissioned. Client-secret rotation policy (180 d / 14 d overlap). Redirect-URI
  governance validation.
- **`mfa/`** — removed as a separate app; MFA is configured and enforced in Zitadel. Django's
  `login/` app renders MFA challenge screens but delegates verification to Zitadel Auth API.
  MFA policy configuration (which factors, mandatory user types) is managed via Zitadel Admin
  API and mirrored in Django config for the Custom Login UI to know which screens to show.
- **`rbac/`** — role catalogue (per-system, versioned), role-binding lifecycle (request → DG
  approval → effective → revoked), separation-of-duties `RuleDefinition`, quarterly access-review
  campaigns. Roles are pushed to Zitadel as user metadata / `urn:zitadel:iam:org:project:roles`
  claims so they appear in issued tokens.
- **`delegation/`** — Governance-Portal webhook ingress, Django-tracked delegation TTL, per-minute
  Celery Beat expiry job. When delegation expires, role binding is revoked in Django and Zitadel
  user metadata/roles are updated.
- **`pam/`** — JumpServer + Vault session records, recording hash anchoring (unchanged).
- **`lifecycle/`** — SCIM 2.0 listener (`/scim/v2/Users`), HRMS event handlers, cleanup jobs.
  Dual-writes: provisions user in Zitadel (via SCIM or Management API) and creates Django
  `User` record. Leaver flow: disables Zitadel user, terminates sessions, updates Django status.
- **`audit/`** — Audit Chain Manager: canonical event emission (includes Zitadel auth events from
  Django's perspective + Zitadel webhook callbacks), SHA-256 chaining, last-hash store,
  System 22 forwarder + outbox, nightly validation.
- **`console/`** — IAM Admin Console API (`/v1/admin/*`): services (write) + selectors (read) +
  serializers (unified envelope). Wraps Zitadel Management API for user/client operations that
  affect the IdP.
- **`core/`** — shared infra: `exceptions.py` (unified envelope + DRF normalisation),
  `middleware.py` (correlation ID, signed-header propagation from System 17, security headers),
  `risk.py` (risk scorer reused by `login/`).
- **`config/`** — split settings: `settings/base.py`, `dev.py`, `staging.py`, `prod.py`.
  Includes Zitadel connection config (host, service account JWT, project ID, org ID).
- **`infra/`** (repo-level) — `terraform/` (K8s/DB/Vault/network, Zitadel Helm), `k8s/` (Django
  manifests/Helm).

Split tests from day one into `tests/unit/`, `tests/api/`, `tests/integration/`, `tests/security/`.

---

## 3. OIDC Auth Flow (Custom Login UI)

The full authentication flow for a user accessing a relying party:

```
User → RP (e.g. Admin Console)
  └→ Redirects to Zitadel /authorize?client_id=...&redirect_uri=...&response_type=code&scope=openid+profile+email
      └→ Zitadel checks for existing session
          ├─ Has session → issues code → redirects to RP callback → RP validates token → done
          └─ No session → redirects to Django Custom Login UI /login?authRequest=...
              └─ Django renders login form
                  └─ User submits username + password
                      └─ Django calls Zitadel Auth API: POST /auth/v1/users/{id}/verify_password
                          ├─ Invalid → render error, no redirect
                          └─ Valid →
                              └─ Django creates Zitadel session (via API or SDK)
                              └─ Zitadel checks MFA policy
                                  ├─ MFA required → redirects Django to /mfa/{factors}
                                  │   └─ User completes MFA challenge
                                  │       └─ Django calls Zitadel Auth MFA verification API
                                  │           └─ Valid → flow continues
                                  └─ MFA not required → skip
                              └─ Zitadel checks consent (first time or new scope)
                                  ├─ Consent needed → redirects Django to /consent
                                  │   └─ User approves → Django calls Zitadel consent API
                                  └─ Consent not needed → skip
                              └─ Django redirects back to Zitadel callback URL
                                  └─ Zitadel issues auth code → redirects to RP
                                      └─ RP exchanges code for tokens at Zitadel /token
                                          └─ RP validates ID token (JWKS, iss, aud, exp, nonce)
                                              └─ RP establishes local session → user is logged in
```

**Key contracts:**
- Django never stores or sees user passwords or MFA secrets
- Zitadel session token is short-lived and managed server-side by Django during the login flow
- Django Custom Login UI receives `authRequest` ID from Zitadel; all callbacks include it
- Custom Login UI endpoints are POST-only (except GET to render forms)
- All communication between Django and Zitadel is mTLS or uses signed service account JWT
- Risk evaluation (geo, device, IP) runs in Django `login/risk.py` and can trigger `acr` step-up
  by passing a signal back to Zitadel

---

## 4. Database & Model Planning

### Zitadel-owned data
Zitadel manages its own PostgreSQL schema for: users, credentials (hashed passwords, MFA
enrolments), OIDC clients/applications, authorization codes, access/refresh/ID tokens, sessions,
consent grants, password reset tokens, MFA recovery codes. **Django never reads or writes these
tables directly** — only via Zitadel's API.

### Django-owned data

- **`User`** (custom, `accounts`) — `id (UUID)`, `zitadel_user_id` (UUID, unique, indexed,
  links to Zitadel user), `email` (unique), `phone`, **no `password` field**, `user_type`
  (`staff|board|nbec|student|external|public`), `status`
  (`pre_active|active|disabled|pending`), `metadata` JSONB
  (staff→`employee_id/department/line_manager_id`, student→`student_id`,
  board→`board_seat/term`, …), `created_at`, `last_login_at`, `hrms_event_ref`. (IAM-F07,
  REQ-F000)
- **`ZitadelUserSync`** — tracks sync state: `user (FK)`, `zitadel_resource_id`, `last_sync_at`,
  `sync_status`, `error_log`. For idempotent SCIM/Zitadel dual-writes.
- **`OIDCClient`** — wraps Zitadel app/client: `zitadel_project_id`, `zitadel_app_id`,
  `client_id`, `client_id_hash`, `lifecycle_state`, `owner_id`, `granted_system_refs[]`,
  `redirect_uris[]`, `post_logout_redirect_uris[]`, `scopes[]`, `secret_rotated_at`,
  `compliance_gate_passed`. (IAM-F11)
- **`Role` / `RoleBinding`** — per-system, versioned role catalogue (`system_code`, `role_id`,
  `permission_strings[]`, `version`, `owner_system`, `effective_from`); binding lifecycle
  (request → DG approval → effective → revoked) with `approver_id`, `effective_from/to`.
  (IAM-F03)
- **`RoleClaim`** — maps Django roles to Zitadel claims:
  `role (FK to Role)`, `zitadel_claim_key` (e.g. `urn:zitadel:iam:org:project:roles`),
  `zitadel_claim_value`.
- **`Delegation`** — `delegator_user_id`, `delegate_user_id`, `scope_client_id`, `role_id`,
  `justification`, `start_at`, `end_at`, `source_event_id` (System 11), `state`
  (`active|expired|revoked`). (IAM-F04)
- **`PamSession`** — `user_id`, `target_id`, `started_at`, `ended_at`, `recording_uri`,
  `recording_sha256`, `vault_lease_id`, `status`. (IAM-F05)
- **`AccessReviewCampaign`** — `period`, `scope`, `reviewer_id`, `decision_count`,
  `completed_at`, `signed_report_ref`. (IAM-F03-03)
- **`AuditEvent`** — `id (bigserial)`, `timestamp` (UTC), `actor_user_id`, `actor_email`,
  `action`, `entity_type`, `entity_id`, `ip_address`, `user_agent`, `channel`
  (`oidc|scim|webhook|pam|console|auth`), `client_id`, `correlation_id`, `result`,
  `redacted_metadata`, `hash_chain_ref`. (IAM-N04)
- **`RuleDefinition`** — `name`, `severity`, `predicate_json`, `version`, `enabled`,
  `approved_by`, `effective_from`. Houses SoD + risk-score rules.
- **`ActiveSession`** — local tracking of Zitadel-issued sessions for Django's own auth:
  `user (FK)`, `session_id` (Zitadel session ID), `jti`, `kind`, `issued_at`, `expires_at`,
  `scope[]`, `claims_hash`, `revoked`. Used for Django-level session checks and audit.

**Model rules:** one-way hash invite/reset tokens; index `zitadel_user_id`, `email`, `user_type`,
`status`, `jti`, and any `expires_at`; append-only audit (logical deletes only); audit retained
10 years, PAM recordings 7 years (SRS §7); all timestamps UTC, displayed in Africa/Accra;
Celery Beat cleanup for expired local state.

---

## 5. API Planning

External traffic enters through **System 17 (Apache APISIX gateway)**, which validates the bearer
token against the **Zitadel JWKS** (`openid-connect` plugin) and propagates signed identity
headers; Django re-validates and applies fine-grained RBAC. Versioned URIs `/api/v{major}/...`
(kebab-case); contract-first.

- **OIDC protocol** — served entirely by **Zitadel** at `https://zitadel.iam.clet.gov.gh/`:
  `.well-known/openid-configuration`, `/jwks`, `/authorize`, `/token`, `/userinfo`,
  `/introspect`, `/revoke`, `/end-session`, `/backchannel-logout`.
- **Custom Login UI (served by Django `login/`):**
  - `GET /login?authRequest=...` — login form
  - `POST /login` — authenticate via Zitadel Auth API
  - `GET /mfa/totp?authRequest=...` — TOTP challenge form
  - `POST /mfa/totp` — verify TOTP via Zitadel Auth API
  - `GET /mfa/webauthn?authRequest=...` — WebAuthn challenge form
  - `POST /mfa/webauthn` — verify WebAuthn via Zitadel Auth API
  - `GET /mfa/sms?authRequest=...` — SMS OTP challenge form
  - `POST /mfa/sms` — verify SMS OTP via Zitadel Auth API
  - `GET /consent?authRequest=...` — consent form
  - `POST /consent` — approve/deny via Zitadel API
  - `GET /password-reset` — password reset form
  - `POST /password-reset` — trigger Zitadel password reset
  - `GET /error?error=...&error_description=...` — error display
- **Admin Console (`/v1/admin/*`, IAM-Admin auth via Zitadel OIDC):**
  - Users: list/create/detail/edit/deactivate/bulk-import (writes to both Zitadel + Django)
  - Roles: catalogue/create/assign/revoke (DG approval for elevated); pushes claims to Zitadel
  - Clients: list/register/promote/rotate-secret (wraps Zitadel project/app API)
  - Audit: search + signed export
- **SCIM 2.0 (`/scim/v2/Users`, signed HRMS auth via Zitadel client_credentials):**
  - POST onboard (creates Zitadel user + Django record)
  - PATCH mover (updates Zitadel metadata + Django record)
  - DELETE/disable leaver (disables Zitadel user, terminates sessions, updates Django)
- **Self-service (`/v1/me*`, Bearer from Zitadel + step-up):**
  - GET/PATCH profile (Django-owned metadata)
  - Active sessions list (from Zitadel API)
  - Single-session terminate (via Zitadel API)
- **Back-channel logout (`/backchannel-logout`, POST from Zitadel):**
  - Receives logout token from Zitadel, invalidates local session records
- **Health/discovery:** liveness, readiness, version. No secrets.

**Response rules:** internal Django API uses the unified envelope (`success`, `message`, `data`,
`meta`, `errors`); gateway-mediated errors use RFC 7807 Problem Details (System 17 contract).
Never return Zitadel API keys, service account tokens, or credentials. Stable error codes:
`AUTHZ_DENIED`, `MFA_REQUIRED`, `STEP_UP_REQUIRED`, `METADATA_MISSING`, `ROLE_CONFLICT`,
`RATE_LIMIT_HIT`, `LOCAL_CREDENTIALS_DETECTED`, `SCHEMA_DRIFT`, `TOKEN_REPLAY`.
**OpenAPI 3.1 + contract tests for every endpoint (IAM-N13).**

---

## 6. RBAC & Permissions

- **Role catalogue lives in Django** (`rbac/`) — per-system, versioned, with permission strings.
- **Roles are surfaced as token claims** via Zitadel user metadata or
  `urn:zitadel:iam:org:project:roles`. When a role binding is created/updated/revoked in Django,
  Django calls the Zitadel Management API to update the user's metadata or project role
  assignment. This ensures the next token issued carries the updated roles.
- **Django control plane** enforces IAM-Admin / DG / Registrar / Internal-Auditor / System-Owner /
  DBA-SRE / Staff-Board-NBEC / Student-External-Public checks for console + SCIM + self-service;
  runs separation-of-duties (e.g. Internal Auditor + IAM Administrator on one account →
  `ROLE_CONFLICT`); routes DG approval for elevated roles.
- **Each relying party** maps `roles[]`/`permissions[]` (from the Zitadel-issued token) to its
  own permission model and enforces business-level access.
- Role catalogue is **per OIDC client, versioned**; default on provisioning = lowest-privilege
  role for the `user_type`; composite roles only with DG approval; mutually-exclusive roles
  rejected at the API + audit-logged *before* binding; role-set changes re-evaluate active
  sessions within 60 s (via Zitadel session termination API); all denials → 403 `AUTHZ_DENIED`
  + audit.

---

## 7. Primary Authentication Flow (Django Custom Login → Zitadel Auth API)

The login flow is a **Django-hosted Custom Login UI** that wraps Zitadel's authentication APIs:

1. **User lands on a relying party** → redirected to Zitadel `/authorize`
2. **Zitadel detects no session** → redirects user to Django `/login?authRequest=...`
3. **Django renders branded login form** (email/username + password)
4. **User submits credentials** → Django POSTs to Zitadel Auth API:
   - `POST /auth/v1/users/{id}/verify_password` with password
   - On success: Django calls Zitadel session creation API, stores session token server-side
5. **Zitadel MFA policy check**:
   - If MFA required → Zitadel redirects Django to `/mfa/{factor}` page
   - Django renders the appropriate MFA challenge form
   - User completes challenge → Django calls Zitadel MFA verification API
   - On success → flow continues
6. **Risk/step-up evaluation** (Django `login/risk.py`):
   - Device fingerprint, IP geo, ASN, time-of-day, known-bad-IP checks
   - High risk → force step-up (additional MFA factor) or deny
   - Step-up also forced for DG/Registrar/IAM-Admin/PAM access
7. **Consent check** → if required, Django renders consent screen, calls Zitadel consent API
8. **Flow complete** → Django redirects back to Zitadel callback URL
9. **Zitadel issues auth code** → RP exchanges for tokens at Zitadel `/token`
10. **RP validates ID token** (JWKS from Zitadel, checks `iss`, `exp`, `nbf`, `iat`, `aud`,
    `kid`, `nonce`/`state`) → establishes local session

**MFA factors** (configured in Zitadel, rendered by Django):
- TOTP (RFC 6238, 6 digits/30 s)
- WebAuthn/passkeys
- SMS-OTP (via System 21, 6 digits, single use, 5-min validity)
- Mandatory + non-bypassable for staff/board/nbec at every interactive login (Zitadel policy)
- Configurable (opt-in) for student/external/public
- Recovery codes handled by Zitadel

**Sessions:**
- Zitadel manages SSO sessions (Redis-backed)
- Idle timeouts: staff/board/nbec 30 min, student 4 h, external 2 h, public 1 h (Zitadel config)
- Absolute lifetime separately configurable (IAM-F07-02)
- Django maintains local session records (`ActiveSession`) for audit + self-service display

---

## 8. Audit Logging

IAM-N04 + the System 22 CALS SRS (SEC-F02) mandate an immutable, cryptographically chained audit
log. **Django `audit/` app owns this entirely** — Zitadel auth events are captured either via:
- Zitadel webhooks (Zitadel can push events to a Django endpoint)
- Django-side interception (every Custom Login UI interaction generates an audit event)
- Zitadel Management API event polling (fallback)

**Capture (auth events):** login success/failure, logout, registration, email verification,
password update, factor add/remove, recovery-code redemption, token replay, refresh-family
revocation, step-up, high-risk denial.

**Capture (domain events):** console actions (account/role/client CRUD, bulk import with file
hash + row counts), SCIM onboard/mover/leaver, exit-access-log generation, PAM revocation,
delegation grant/expiry/revoke, DG 24-h notice, PAM session lifecycle, access-review decisions
+ signed reports.

**Canonical AuditEvent JSON** (SEC-F02-01): the §4 `AuditEvent` fields.

**Hash chain:** `hash_chain_ref = SHA256(prev_hash ‖ canonical_event)`; last hash persisted;
nightly Celery job rebuilds + verifies; signed PDF+JSON export with verification instructions
for the Auditor-General.

**Never log:** raw passwords/hashes, OTPs, full recovery codes, Zitadel service account tokens,
client secrets, refresh-token values, or unredacted PII beyond what the SRS allows.

---

## 9. Integrations

- **Zitadel → Django (Custom Login UI):** redirect-based protocol. Zitadel sends `authRequest`
  parameter; Django performs auth via Zitadel Auth API; Django redirects back to Zitadel's
  callback URL. mTLS between services in production.
- **Django → Zitadel (Management API):** gRPC or REST. Service account JWT (signed by Zitadel,
  stored in Vault). Used for user CRUD, role claim updates, client lifecycle, session
  termination, event polling.
- **Django → Zitadel (Auth API):** REST. Used during Custom Login UI flow. Authenticated via
  session tokens (not service account).
- **HRMS (System 09)** — inbound SCIM 2.0 + signed webhooks. Django `lifecycle/` app receives
  and dual-writes to Zitadel (via Management API or Zitadel SCIM endpoint) + Django DB.
  Phase 1 stub; cutover is config.
- **Governance Portal (System 11)** — signed delegation webhooks (HMAC-SHA256). Django applies
  binding, tracks TTL locally, updates Zitadel user metadata/roles on change. Phase 1 stub.
- **API Gateway (System 17, Apache APISIX)** — validates IAM bearer tokens via the **Zitadel
  JWKS** (`openid-connect` plugin); propagates signed identity headers (`sub`, `aud`, `scope`,
  `consumer_id`) upstream; mTLS internal + government; per-consumer scope/quota; RFC 7807 errors.
  Kafka is the async backbone.
- **Communications (System 21)** — email verification, MFA OTP, invite/reset links,
  delegation-expiry notices. Never log raw OTPs. Django calls System 21 API or uses Zitadel's
  built-in notification channels.
- **Cybersecurity, Audit & Logging (System 22 / CALS)** — receives every security event + the
  audit chain; Django runs the Audit Chain Manager and forwards canonical events (outbox replay
  on failed delivery). Phase 1 stub; cutover is config.
- **Physical Access Control (S160a)** — on HRMS exit, IAM propagates door-access revocation with
  PAM revocation.
- **Off-Campus Auth Proxy / EZproxy (S120)** — library e-resource federation consuming Zitadel
  tokens.
- **22 relying parties** — each registers as a confidential/public OIDC client in Zitadel,
  validates JWTs locally against the Zitadel JWKS, builds its own permission model from claims,
  participates in front- and back-channel logout.

---

## 10. Validation Rules

**Token (Zitadel-enforced):** RS256 or better; `iss` matches Zitadel issuer; `exp/nbf/iat`
enforced; `aud` matches the client; `kid` resolves in the published JWKS; `nonce`+`state`
mandatory; PKCE S256 only; redirect URIs exact match.

**Client/lifecycle (Django-enforced + Zitadel-enforced):** prod redirect URIs exact; public
clients PKCE-only (no static secret); Implicit + password grants disabled in Zitadel project
config; secrets rotate ≥ 180 d (14-day overlap); sandbox→prod promotion needs green sandbox
tests + compliance-gate pass + IAM-Admin approval.

**User/onboarding:** email globally unique, RFC 5322 + disposable-domain block-list;
`user_type` ∈ {staff,board,nbec,student,external,public}; staff must reference HRMS
`employee_id`, students a verified `student_id` (else `METADATA_MISSING`); staff/board/nbec
self-registration disabled; email-verification link single-use, 24-h validity; unverified > 7
days purged; mutually-exclusive roles cannot coexist.

**MFA (Zitadel-enforced, Django UI):** mandatory + non-bypassable for staff/board/nbec;
DG/Registrar/IAM-Admin cannot use SMS-only; TOTP RFC 6238; SMS via System 21 only, never
logged; 10 single-use recovery codes; factor lockout 5/5 min → 15 min; step-up `acr` for
DG/Registrar/IAM-Admin/PAM areas + high-stakes student/public actions.

**Transport/rate/residency:** TLS 1.3 end-to-end; Zitadel + Django rate-limit/brute-force
(5 fails/5 min/IP → 15-min throttle + System 22 event); all identity/audit/PAM data resides in
Ghana (IAM-N10); AES-256 at rest; Zitadel handles HSM/KMS-backed signing key (IAM-N09).

**Compliance gate (Django-enforced):** every onboarded RP must pass the `SRS-IAM-F01-04`
compliance gate before production cutover — verifies no parallel password store exists at the RP.

---

## 11. Testing Strategy

- **Unit:** Django-side: claim mapping from Zitadel token → Django user; audit creation,
  redaction, hash-chain rebuild→verify; SoD predicate eval; risk scorer; `acr` step-up logic;
  password-policy validators; Zitadel API client retry/timeout/error handling; SCIM-Zitadel
  dual-write idempotency.
- **API:** authn/unauthn per endpoint; invalid iss/expired/wrong-aud/wrong-alg/unknown-kid/
  missing-sub **returned by Zitadel** — test that Django correctly propagates/rejects them;
  role-conflict/mandatory-MFA/factor-lockout/brute-force/step-up failures (Zitadel behaviour,
  Django UI display); bulk import mixed rows + row-level report; unified-envelope shape;
  SCIM onboard/mover/leaver signed; delegation webhook valid/invalid signature + eligibility +
  expiry.
- **Integration:** full OIDC dance against Zitadel with a sample RP (discovery → authorize →
  Custom Login UI → MFA → consent → token → userinfo → refresh → revoke → logout); JWKS
  validation incl. rotation overlap (Zitadel-managed); back-channel logout delivery ≤ 30 s
  (Zitadel emits → Django receives); Communications stub idempotent retries; System 22 chain
  delivery + outbox retry + root verification; HRMS SCIM SLAs; PAM happy path (Vault lease →
  JumpServer → recording SHA-256 → System 22 anchor); Zitadel API client integration tests
  against a test Zitadel instance.
- **Security:** no Implicit/password grant reachable on any Zitadel project config; no parallel
  password store on any RP (the compliance gate); no secrets in Git/.env/TF-state (CI scan);
  brute-force lockout fires + System 22 event; admin endpoints only on the IAM-Admin allow-list;
  Zitadel service account token never leaked.
- **Performance/resilience:** Custom Login UI page render < 200 ms p95, Zitadel API calls from
  Django < 500 ms p95 (IAM-N05); quarterly DR drill 15-min RTO zero auth failures (IAM-N01);
  10× horizontal scale (IAM-N12) — stateless Django pods, Zitadel handles IdP scaling.

---

## 12. Implementation Order

### Sprint 0 — Foundation lock-in & base infra
1. Record `DEV-IAM-01-R` (Zitadel IdP decision reversal)
2. Select Zitadel deployment model (K8s Helm chart, version, external or embedded DB)
3. Stand up Zitadel cluster on K8s with PostgreSQL (sync replication), Redis
4. Configure Zitadel: organization, project(s), Custom Login UI registration
5. Create Zitadel service account for Management API access (store key in Vault)
6. Set up Django project skeleton: custom user model (no password field), split settings
7. Sign off Phase 1 backlog + compliance-gate format

### Phase 1 — Core Identity Substrate & SSO with Custom Login UI
Covers IAM-F01, F02, F03, F07, F10, F11, REQ-F000, and NFRs N02–N06, N09, N11, N13.
1. **Zitadel OIDC provider bring-up** — verify discovery, JWKS, authorize/token/userinfo/
   introspect/revoke, PKCE S256 enforcement, client_credentials, disabled Implicit + password
   grants.
2. **Zitadel OIDC client registration** — create the Admin Console app in Zitadel (confidential,
   Auth Code + PKCE)
3. **Django `login/` app** — Custom Login UI: login form, Zitadel Auth API integration,
   session creation, redirect flow. Test full Zitadel → Django → Zitadel → RP dance.
4. **MFA screens** — TOTP, WebAuthn, SMS challenge forms in Django, wired to Zitadel Auth API
   MFA endpoints
5. **Consent screen** — Django consent form + Zitadel consent API integration
6. **Django `accounts/` + `oidc_rp/` apps** — User model, `mozilla-django-oidc` RP setup,
   token validation against Zitadel JWKS, claim mapping
7. **Django `console/` app** — Admin Console API: Users CRUD (wraps Zitadel Management API +
   Django DB), roles catalogue, audit search
8. **MFA policy** — configured in Zitadel per user type; Custom Login UI adapts screens based
   on Zitadel policy response
9. **Custom token claims** — configure Zitadel user metadata or project roles to carry
   `roles[]`, `portal_access[]`, `permissions[]`
10. **Django `audit/` app** — Audit Chain Manager (SHA-256), event capture from login/console/
    SCIM actions
11. **Django `lifecycle/` app** — SCIM 2.0 listener + HRMS stub, bulk import, dual-write to
    Zitadel
12. **Compliance gate** — per onboarded RP, verify no parallel password store
13. **Phase 1 demo** — Admin creates staff user → Zitadel create → invite → password + MFA via
    Custom Login UI → SSO into sandbox RP → elevated role via DG approval → audit chain verified

### Phase 2 — Lifecycle Automation, Self-Service & Resilience
Covers IAM-F06, F08, F09, N01, N07, N12, N14.
1. Real HRMS SCIM 2.0 + signed webhooks: joiner ≤ 1 h, mover ≤ 1 h, leaver disable ≤ 4 h,
   session terminate ≤ 60 s (via Zitadel Management API session termination)
2. Self-service registration (student/external/public): email verification, branded UI,
   rate limits, captcha, anomaly detection; unverified accounts purged after 7 days (Django
   cleanup job + Zitadel API user removal)
3. RP-Initiated Logout (`end_session` + `id_token_hint`) + back-channel logout (Zitadel emits
   to Django `/backchannel-logout`) ≤ 30 s
4. Quarterly DR drill (Zitadel HA + Django stateless, 15-min RTO, zero auth failures)
5. Mandatory-student-MFA rollout (Zitadel policy toggle)

### Phase 3 — Delegation, PAM & Access-Review Rhythm
Covers IAM-F04, F05, F03-03.
1. Signed delegation webhooks from System 11: auto-grant ≤ 60 s (add role binding in Django +
   push role claims to Zitadel); Django tracks TTL and auto-expires (per-minute Celery Beat job);
   revocation terminates Zitadel sessions
2. JumpServer + Vault PAM: short-lived credentials, video + keystroke recording, WORM storage,
   7-year retention, SHA-256 anchored daily to System 22, Auditor read-only with tamper detection
3. Quarterly access-review campaigns (keep/revoke/change-role), revocations within 5 business
   days, signed DG+Admin report exportable to the Auditor-General; role-mining recommendations

### Operational Rhythm
- Quarterly: DR drill + access review
- Secret rotation (Zitadel app secrets, Django-to-Zitadel service account JWT)
- Monthly: restore drill
- Daily: audit-chain anchor verification

---

## 13. Zitadel Setup Checklist

### Cluster
- [ ] Zitadel Helm chart deployed on K8s (production: 3+ replicas)
- [ ] PostgreSQL with synchronous streaming replication (RPO 0)
- [ ] Redis for session cache
- [ ] Ingress configured with TLS 1.3
- [ ] mTLS between Zitadel and Django (Custom Login UI + API calls)

### Organization & Project
- [ ] Organization created (e.g. `clet-ghana`)
- [ ] IAM project created (e.g. `iam-system-19`)
- [ ] Custom Login UI registered:
  - [ ] Login URL: `https://iam-auth.clet.gov.gh/login`
  - [ ] MFA URLs: `https://iam-auth.clet.gov.gh/mfa/{factor}`
  - [ ] Consent URL: `https://iam-auth.clet.gov.gh/consent`
  - [ ] Password reset URL: `https://iam-auth.clet.gov.gh/password-reset`
  - [ ] Error URL: `https://iam-auth.clet.gov.gh/error`
- [ ] Implicit + ROPC grants disabled at project level
- [ ] PKCE S256 required for all public clients
- [ ] Client credentials grant enabled (for S2S)

### Service Users
- [ ] Management API service user created (Django-to-Zitadat admin operations)
- [ ] Service user JWT signed and stored in HashiCorp Vault
- [ ] Service user granted `IAM_OWNER` or appropriate scoped roles
- [ ] Auth API access configured (for Custom Login UI verification calls)

### Applications (OIDC Clients)
- [ ] Admin Console app (confidential, Auth Code + PKCE)
- [ ] Each RP registered as a separate Zitadel app
- [ ] Sandbox environment per RP for compliance gate testing
- [ ] Back-channel logout configured per app

### SCIM
- [ ] Zitadel SCIM endpoint enabled (or plan to use Management API for user provisioning)
- [ ] SCIM bearer token configured and stored in Vault

### Security
- [ ] Signing key algorithm set to RS256 (minimum)
- [ ] HSM or cloud KMS integration for signing keys (production)
- [ ] MFA policy defined: mandatory staff/board/nbec, configurable others
- [ ] Password policy configured (length ≥ 12, complexity)
- [ ] Session idle/absolute timeouts configured
- [ ] Rate limiting configured
- [ ] Audit webhook endpoint configured: `https://iam-audit.clet.gov.gh/zitadel-events`
- [ ] Residency: data stays in Ghana (IAM-N10) — confirm Zitadel DB region

---

## 14. Risks & Open Questions

- **`DEV-IAM-01-R` must be formally recorded.** Ensure the team explicitly agrees to rescind
  the Django-native approach and adopt Zitadel. Re-confirm at each phase gate.
- **Custom Login UI contract is Zitadel-version-specific.** Verify the exact redirect contract,
  `authRequest` parameter handling, session token format, and MFA verification API for the
  chosen Zitadel version (Zitadel v2.x API vs v3 alpha). Lock version in Sprint 0.
- **Zitadel Auth API for password verification** — confirm the exact endpoint, request/response
  format, rate limits, and whether MFA challenge APIs are available for server-side verification.
  If the Auth API is insufficient, consider an alternative: Zitadel's login UI rendered as an
  iframe, or using the Zitadel Console API with a custom theme instead.
- **Zitadel SCIM maturity.** If Zitadel SCIM does not support the full joiner/mover/leaver
  workflow, fall back to provisioning via the Management API (REST/gRPC). The Django
  `lifecycle/` app can abstract this.
- **Zitadel event webhooks.** Confirm Zitadel can push auth events (login, logout, MFA, etc.)
  to a Django endpoint for audit chain capture. If not, Django must capture these from its
  Custom Login UI interactions.
- **Risk-based step-up.** Zitadel's native step-up may be limited. Django's `login/risk.py`
  can pass context to Zitadel via `acr_values` during the auth request. Verify Zitadel supports
  custom `acr` handling.
- **Residency (IAM-N10).** Zitadel must be deployed in Ghana (GCP africa-south1 region or
  on-prem) with data residency enforced. Confirm the Zitadel deployment meets this.
- **WebAuthn helpdesk recovery** — document recovery path (Zitadel recovery codes + Admin
  Console reset) for WebAuthn-only DG/Registrar/IAM-Admin accounts; validate against Ghana
  device/browser support.
- **Zitadel version lock-in risk.** Zitadel v2 is stable; v3 is in development. Evaluate the
  API stability, Custom Login UI support, and migration path before committing.
