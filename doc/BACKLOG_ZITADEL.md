# IAM (System 19) Backlog — Zitadel Edition

> **What this is.** The original product backlog was written against **Keycloak** (it lives with the
> `iam-1.0` codebase). The active `iam/` codebase (this repo, "iam-3.0") uses **Zitadel** as the
> external OpenID Connect provider, with Django as the resource server, Admin Console, SCIM gateway,
> audit-chain manager, and Custom Login UI host. This document is the **same backlog re-expressed
> against Zitadel**, with each story's **Status verified against the code on 2026-06-25**.
>
> **Source of truth** for the rewrite: `iam/.claude/skills/iam-zitadel-backend/SKILL.md` (the
> blueprint, which records `DEV-IAM-01-R` — the Zitadel IdP decision) and
> `iam/.claude/skills/zitadel-knowledge-patch/SKILL.md` (Zitadel v3→v4.13 primitives). Every story
> still traces to its original `SRS-IAM-*` / `IAM-*` requirement ID.

**Status legend:** ✅ Done · 🟡 Partial · ❌ Not started · ⬅️ **regression** — was implemented in
`iam-1.0` (Keycloak) but is missing here.

---

## Implementation status snapshot (re-verified 2026-06-26)

| Epic | State | Headline |
|---|---|---|
| IAM-F01 OIDC IdP + PKCE | 🟡 | Login flow works; **no Terraform IaC** (config is imperative). |
| IAM-F02 MFA | ✅ | TOTP/WebAuthn/OTP via Session API; recovery codes now implemented + routed. |
| IAM-F03 RBAC + SoD | ✅ | Catalogue, approval, SoD, access-review sweeper all done + scheduled. |
| IAM-F07 User types | 🟡 | Model + metadata done; per-type session/MFA policy config still thin. |
| IAM-F10 Token claims | ✅ | Actions V2 `complement_token` wired + claim schema published; CLM-4 filtering partial. |
| REQ-F000 Admin Console | ✅ | Users/roles/clients/audit + dashboard + RBAC-matrix now present. |
| IAM-F06 HRMS lifecycle | 🟡 | SCIM + handlers + timed jobs done; **hrms-stub + admin hrms-events/replay missing**. |
| IAM-F11 OIDC clients | ✅ | Lifecycle + scheduled auto-rotation + `check_zitadel_drift` command. |
| IAM-N04 Audit chain | ✅ | Per-event chain + verify + daily anchor + outbox forwarding all scheduled. |
| IAM-F08 Self-registration | 🟡 | Reg/verify + purge scheduled; disposable/per-IP block-lists still thin. |
| IAM-F09 Logout / SLO | 🟡 | Back-channel endpoint exists; delivery-SLA + failure audit unverified. |
| IAM-F04 Delegation | ✅ | Model + webhook + scheduled expire + DG-24h-notice. |
| IAM-F05 PAM | 🟡 | Recording-anchor + cleanup tasks added; Vault/JumpServer infra not built. |
| IAM-N08/N05 Observability | 🟡 | Prometheus metrics + OTel + `/health/metrics`; **no Grafana/Loki/SLO dashboards/contract tests**. |
| IAM-N01/N07/N12/N14 HA/DR | ❌ | One k8s manifest; no replication/backups/load-test. |
| IAM-N10/N11 Residency/DPIA | ❌ | No inventory endpoints or sign-off. |

**Resolved since 2026-06-25:** the scheduled-jobs gap is closed — `iam-1.0` ran 8 beat jobs; this
repo now schedules **16** (all register cleanly), with daily jobs on fixed-time `crontab` schedules.
Recovery codes, admin dashboard, RBAC matrix, Actions V2 claims, claim-schema publish, and
`check_zitadel_drift` have all landed. **Remaining real gaps:** Terraform IaC (F01), HRMS admin
surface (F06), the Grafana/Loki/SLO/contract-test half of observability (N08/N05), PAM heavy infra
(F05), and HA/DR/residency (N01/N10).

---

## Keycloak → Zitadel translation key

| Keycloak concept (old backlog) | Zitadel equivalent (this repo) | Notes |
|---|---|---|
| Realm | **Organization** (`OrganizationService` v2) | User-types separated by metadata/policy, not separate realms. |
| Client | **Application** inside a **Project** | PKCE per app. |
| `keycloak` Terraform provider | **`zitadel/zitadel`** Terraform provider (v2.11) | Or v2 APIs via `clients/`. *(Not present yet — no `terraform/` dir.)* |
| Direct Access Grants (ROPC) | **Not supported by Zitadel at all** | "Disable ROPC" → assert unavailable; no Django password field. |
| Implicit grant | Disabled **per application** | Must be explicitly off per app. |
| Protocol/claim mappers | **Project-roles claim** + **user metadata** scope + **Actions V2** (`restCall`) | |
| User attributes | **User metadata** | |
| Audience mapper | `urn:zitadel:iam:org:project:id:{id}:aud` scope | Required or introspection returns `active:false`. |
| Event Listener SPI | **Actions V2 webhook target** + Django-side capture | No SPI jar. |
| Authenticator SPI (SMS/risk/ACR) | **Session API** checks (`otpSms`/`totp`/`webAuthN`) + Actions V2 + `core/risk.py` | |
| OTP policy / brute-force | **Lockout policy** + **login policy** | |
| Realm signing-key rotation | **WebKeys V2** (`WebKeyService`), RS256, managed | |
| `KEYCLOAK_VALID_AUDIENCES` | `ZITADEL_VALID_AUDIENCES` | |
| `kc_token_size_bytes` | `zitadel_token_size_bytes` | |
| `check_keycloak_drift` job | `check_zitadel_drift` | *(Not present yet.)* |
| SCIM (HRMS → IAM) | Django `lifecycle/` SCIM → dual-write to Zitadel `UserService` v2 + Django | |
| Recovery codes | ⚠️ Not implemented here — see **Open items**. | |

---

## Epic IAM-F01 — Centralised OIDC IdP with Auth Code + PKCE
**`SRS-IAM-F01`** — Zitadel is the centralised OIDC IdP; all user-facing login uses Auth Code + PKCE.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| IAM-F01-1 | Centralised OIDC IdP with Auth Code + PKCE | ✅ | `login/` + `login-app/` drive the Zitadel auth flow; `oidc_rp/` validates tokens. |
| F01-1 | ROPC unavailable; no local-password fallback | ✅ | Zitadel has no ROPC; `accounts.User` has no password field. |
| F01-2 | Enforce PKCE S256 on all public apps via Terraform | 🟡 | Apps configured via `scripts/bootstrap_zitadel.py`; **no `terraform/` dir**. |
| AUTH-4 | `state`/`nonce` replay protection on callback | ✅ | Handled by `mozilla-django-oidc` in `oidc_rp/`. |
| AUTH-3 | Fail closed when `ZITADEL_VALID_AUDIENCES` empty | 🟡 | Verify the guard exists for prod. |
| AUTH-5 | Native refresh rotation + family revocation; mirror in `ActiveSession` | ✅ | Zitadel-native; `api/auth/*` mirrors sessions. |
| F01-3 | Terraform skeleton: org, project, roles, scopes, claim mappers | ❌ | No `terraform/` dir; config is imperative (`bootstrap_zitadel.py`). |
| D9 | Split `users/tests.py` into unit/api/integration/security | 🟡 | `tests/{unit,api,integration,security}` dirs exist; coverage partial. |
| — | `bandit` + `ruff` security-lint in CI | 🟡 | `ruff` in `pyproject.toml`; confirm `bandit` + CI wiring. |

---

## Epic IAM-F02 — Multi-Factor Authentication
**`SRS-IAM-F02`** — Mandatory MFA staff/board/nbec (TOTP); WebAuthn for DG/Registrar/IAM-Admin;
SMS-OTP via System 21; 10 recovery codes; 5-fail/5-min lockout.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| MFA-1 | Force TOTP for staff/board/nbec via login policy | ✅ | `scripts/configure_mfa.py`; `login-app` TOTP via Session API `totp`. |
| MFA-2 | WebAuthn/passkeys for DG/Registrar/IAM-Admin | ✅ | `login-app/src/lib/webauthn.ts` → Session API `webAuthN`. |
| MFA-5 | 10 single-use recovery codes on enrolment | ✅ | `accounts/recovery.py` (hashed + masked), `RecoveryCode` model, routed `v1/me/recovery-codes` + `/verify`. |
| MFA-6 | Lockout 5/5 min → 15-min cooldown | 🟡 | Zitadel lockout policy; confirm values configured. |

---

## Epic IAM-F03 — RBAC with Least Privilege
**`SRS-IAM-F03`** — Per-system versioned role catalogue, DG approval for elevated roles, SoD,
quarterly access-review, default least-privilege role.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| RBAC-1 | `Role` model: version, effective dates, owner_system | ✅ | `rbac/models.py`. |
| RBAC-2 | `RoleAssignmentRequest` DG-approval workflow | ✅ | `console` `role-bindings/{approve,reject}` queue. |
| RBAC-3 | SoD mutually-exclusive pairs via `RuleDefinition` | ✅ | `rbac/models.py` `RuleDefinition` + `rbac/services.py`. |
| RBAC-8 | Default least-privilege role per `user_type` on creation | 🟡 | Confirm default-role assignment on user create. |
| RBAC-4 | Quarterly access-review + revocation-SLA sweeper | ✅ | Campaigns/items/decide/export + scheduled `execute_overdue_access_review_revocations` (04:00). |

---

## Epic IAM-F07 — Distinct User-Type Management with Custom Metadata
**`SRS-IAM-F07`** — Six `user_type`s with required metadata mirrored into Zitadel, per-type policy.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| TYPE-1/2 | `user_type` field + metadata JSONB + validation | ✅ | `accounts.User`. |
| TYPE-4 | Mirror `user_type`/metadata as Zitadel user metadata | 🟡 | Pushed via console/`setup_systems`; confirm metadata-scope claim wiring. |
| TYPE-5 | Per-type session lifetime / MFA mandate / password complexity | 🟡 ⬅️ | `configure_mfa.py` only; **no `configure_session_policies` equivalent** (`iam-1.0` had it). |

---

## Epic IAM-F10 — Custom Token Claims for Authorization Decisions
**`SRS-IAM-F10`** — Custom claims for `user_type`, `portal_access[]`, `permissions[]`.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| CLM-1 | Inject claims via Actions V2 + project-roles claim | ✅ | `oidc_rp/actions_v2.py:complement_token` routed at `/api/actions/complement-token`; `scripts/configure_actions_v2.py` binds `preaccesstoken`. |
| CLM-2 | Per-client audience via project-aud scope | 🟡 | Confirm aud scope set per client (needed for introspection). |
| CLM-3 | Publish IAM claim JSON Schema at `/.well-known/...` | ✅ | `oidc_rp/claims_schema.py` routed at `.well-known/iam-claims-schema.json`. |
| CLM-4 | Per-client claim filtering | 🟡 | Partial — verify only granted scopes/roles are emitted per client. |

---

## Epic REQ-F000 — IAM Admin Console
**`REQ-F000`** — Dashboard KPIs, user CRUD w/ filters, bulk import/export, RBAC matrix, audit w/
signed export, OIDC client management. *(Django `console/`.)*

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| — | Admin dashboard KPI endpoint | ✅ | `console/views/dashboard.py` routed `v1/admin/dashboard`. |
| — | User list with filters (`user_type`/status/role/org) | ✅ | `console/views/users.py` `users_list`. |
| — | RBAC matrix viewer endpoint | ✅ | `console/views/rbac_matrix.py` routed `v1/admin/rbac/matrix`. |
| — | Bulk CSV/Excel import w/ row-level errors | ✅ | `users/bulk-import`. |
| — | Audit search + signed export | ✅ | `audit/{search,verify,export}`. |
| Cross | Remove AMS `seed_superadmin` duplicate user | ❌ | Cross-service cleanup. |
| Cross | CI assertion NBES `ROLES` == IAM `seed_system_roles` | ❌ | Cross-service CI. |

---

## Epic IAM-F06 — Automated User Lifecycle from HRMS (SCIM 2.0)
**`SRS-IAM-F06`** — Joiner ≤ 1 h, mover ≤ 1 h, leaver login ≤ 60 s / disable ≤ 4 h, sessions revoked.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| LCM-1 | SCIM listener + HMAC verification | ✅ | `scim/v2/Users*`, `lifecycle/hrms-webhook`. |
| LCM-2/5 | Joiner activate pre-provisioned user at `start_date` ≤ 1 h | ✅ | `_process_joiner` + scheduled `activate_pre_active_accounts` (hourly). |
| LCM-3 | Mover: update metadata + reassign roles ≤ 1 h | ✅ | `_process_mover`. |
| LCM-4 | Leaver: disable ≤ 60 s, deactivate ≤ 4 h | ✅ | `_process_leaver` immediate + scheduled `finalize_leaver_disable` (hourly). |
| LCM-6 | Audit all SCIM events | ✅ | Audit emit on lifecycle. |
| — | `hrms-stub` mgmt command | ❌ | Only `seed_iam`, `setup_systems` commands exist. |
| — | HRMS-events admin + replay + move-conflict resolve | ❌ ⬅️ | `iam-1.0` had `admin/hrms-events*`, `move-conflicts*`. |

---

## Epic IAM-F11 — OIDC Client Registration and Lifecycle
**`SRS-IAM-F11`** — Lifecycle onboarding→…→decommissioned; 180-day rotation, 14-day overlap.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| F01-7 | App lifecycle transitions | ✅ | `clients/{promote,suspend,activate}`. |
| F01-4 | `rotate_due_clients`: 180-day auto-rotation | ✅ | `clients/tasks.py:rotate_due_client_secrets` scheduled (03:30) + manual endpoint. |
| — | `check_zitadel_drift` nightly CI job | ✅ | `clients/management/commands/check_zitadel_drift.py` (diffs Zitadel vs Django, non-zero exit, `--fix`). |
| — | OIDC clients admin list / status | ✅ | `console/views/clients.py`. |

---

## Epic IAM-N04 — Immutable Audit Log with Hash Chain
**`SRS-IAM-N04`** — Append-only SHA-256 chain; daily root anchored to System 22; 10-year retention.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| AUD-1/2 | `hash_chain_ref` + `channel` columns | ✅ | `audit/models.py`. |
| — | Per-event SHA-256 chaining + verify | ✅ | `audit/chain.py` (`anchor_event` at emit, `verify_chain`). |
| AUD-3/4 | Actions V2 webhook routes Zitadel events into audit | 🟡 | Django-side emit works; **no Zitadel Actions V2 target** for native auth events. |
| AUD-3 | `anchor_chain_daily`: daily root → System 22 | ✅ | `audit/tasks.py:anchor_chain_daily` emits daily root + runs `verify_chain`, scheduled 02:00. |
| — | `forward_outbox` to System 22 | ✅ | Registered via `audit/tasks.py`, scheduled every 5 min (no-ops until `SYSTEM_22_AUDIT_URL` set). |
| AUD-4 | 10-year retention, no purge | ✅ | `AUDIT_RETENTION_YEARS = 10`. |

---

## Epic IAM-F08 — Self-Service Account Registration
**`SRS-IAM-F08`** — Branded registration; single-use 24-h email verification; rate limits; block-lists.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| SS-1/3 | Self-registration + email verification | 🟡 | `login/register` + `verify` via login-app/Zitadel. |
| SS-2 | Disable self-registration for staff | 🟡 | Via Zitadel org registration policy; confirm. |
| SS-4/5 | Per-IP/per-email rate limits | 🟡 | `RATE_LIMIT_PATHS` + scheduled `purge_unverified_registrations` (03:00); per-email limit still thin. |
| SS-6 | Disposable-domain block-list | ❌ | Not present. |

---

## Epic IAM-F09 — Single Logout and Global Sign-Out
**`SRS-IAM-F09`** — RP-Initiated + front/back-channel logout < 30 s; `LogoutDeliveryFailure` audit.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| SLO-1 | `frontchannel`/`backchannel_logout_uri` per app | 🟡 | Configured via bootstrap; no Terraform. |
| SLO-2/3 | Back-channel logout < 30 s + failure audit | 🟡 | `oidc_rp/backchannel.py` endpoint exists; SLA + failure-audit unverified. |
| MFA-3 | SMS-OTP fallback via System 21 | 🟡 | Session API `otpSms`; SMS provider integration stubbed. |
| MFA-4 | Risk-engine + ACR step-up | 🟡 | `core/risk.py` exists; confirm `acr_values` step-up wiring. |
| F01-4 | 90-day signing-key rotation (WebKeys V2) | 🟡 | Relies on Zitadel default rotation; no explicit config. |
| AUD-5 | Signed audit export (tar/zip + hash-chain + DG sig) | ✅ | `audit/export`. |

---

## Epic IAM-F04 — Delegation Enforcement
**`SRS-IAM-F04`** — HMAC-signed delegation webhooks; grant ≤ 60 s; auto-expire; DG notice 24 h before.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| DEL-1/2 | `Delegation` model + HMAC webhook | ✅ | `delegation/models.py`, `delegation/webhook`. |
| DEL-3 | `expire_due_delegations` auto-expiry | ✅ | `delegation.tasks.expire_delegations` scheduled (60 s). |
| DEL-4 | DG notification 24 h before expiry | ✅ | `delegation.tasks.notify_dg_24h_before_expiry` scheduled (hourly). |
| DEL-5 | Audit delegation events | ✅ | Audit emit with delegation channel. |

---

## Epic IAM-F05 — Privileged Access Management (PAM)
**`SRS-IAM-F05`** — JumpServer + Vault JIT access; recording in WORM; SHA-256 anchored.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| PAM-1/3 | Vault dynamic creds + JumpServer | ❌ | Not built. |
| PAM-4 | JumpServer uses Zitadel OIDC only | ❌ | Not built. |
| PAM-2/5 | Recording SHA-256 anchored daily | 🟡 | `pam.tasks.anchor_recording_hashes_daily` scheduled (02:30); depends on real recordings. |
| PAM-6 | Revoke leases + kill sessions on leaver ≤ 60 s | ❌ | Not built. |
| PAM-7 | Auditor read-only PAM access | ❌ | Not built. |
| — | Session start/end skeleton | 🟡 | `pam/sessions`, `pam/sessions/{id}/end` exist as stubs. |

---

## Epic IAM-N08 / N05 — Observability, Monitoring, SLOs
**`SRS-IAM-N08`, `N05`** — Prometheus + Grafana + Loki + OTel; login p95 < 2 s; introspection < 50 ms.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| — | Prometheus + Grafana + Loki | 🟡 | `core/metrics.py` (Counter/Gauge/Histogram) + `/health/metrics`; **Grafana/Loki stack not deployed**. |
| — | OpenTelemetry tracing | ✅ | `core/otel.py`, feature-flagged via `OTEL_ENABLED`. |
| — | SLO dashboards | ❌ | Not present. |
| — | `zitadel_token_size_bytes` metric + CI gate | ❌ | Not present. |
| — | Schemathesis contract tests (OpenAPI 3.1) | ❌ | `drf-spectacular` schema served; no contract tests. |

---

## Epic IAM-N01 / N07 / N12 / N14 — HA, DR, Backups, Scaling
**`SRS-IAM-N01,N12,N14`** — Sync PG replication (RPO 0); active-active k8s; 10× scale; daily backups.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| N07 | k8s active-active deployment | 🟡 | Only `infra/k8s/django-deployment.yaml`. |
| N01 | Sync PG replication + DR drill | ❌ | Not present. |
| N14 | Daily encrypted backup + restore drill | ❌ ⬅️ | `iam-1.0` had `admin/backups`, `dr-runs`. |
| N12 | 10× horizontal capacity test | ❌ | Not present. |

---

## Epic IAM-N10 / N11 — Data Residency, DPIA, Legal Compliance
**`SRS-IAM-N10,N11`** — Data in Ghana; annual DPIA; sign-off documented.

| Key | Summary (Zitadel) | Status | Evidence / gap |
|---|---|---|---|
| N10 | Document residency (incl. Zitadel DB region) | ❌ ⬅️ | `iam-1.0` had `admin/residency` + review. |
| N11 | DPIA sign-off under Act 843 | ❌ | Not present. |
| N10 | Annual residency review stamp | ❌ ⬅️ | `iam-1.0` had `residency-review`. |

---

## Scheduled jobs (Celery Beat) — RESOLVED (2026-06-26)

`iam-1.0` ran 8 beat jobs; this repo now schedules **16**, all registering cleanly. Daily jobs use
fixed-time `crontab` (Africa/Accra) so they run off-peak and survive restarts predictably.

| Job (SRS) | Task | Schedule |
|---|---|---|
| `expire_due_delegations` (F04) | `delegation.tasks.expire_delegations` | 60 s |
| audit `forward_outbox` (N04) | `audit.forwarder.forward_outbox` | 5 min |
| `anchor_chain_daily` (N04) | `audit.tasks.anchor_chain_daily` | 02:00 |
| `activate_pre_active_accounts` (F06) | `lifecycle.tasks.activate_pre_active_accounts` | hourly |
| `finalize_leaver_disable` (F06) | `lifecycle.tasks.finalize_leaver_disable` | hourly |
| `purge_unverified_registrations` (F08) | `lifecycle.tasks.purge_unverified_registrations` | 03:00 |
| `rotate_due_client_secrets` (F11) | `clients.tasks.rotate_due_client_secrets` | 03:30 |
| `execute_overdue_access_review_revocations` (F03) | `rbac.tasks.execute_overdue_access_review_revocations` | 04:00 |
| `notify_dg_24h_before_expiry` (F04) | `delegation.tasks.notify_dg_24h_before_expiry` | hourly |
| `anchor_recording_hashes_daily` (F05) | `pam.tasks.anchor_recording_hashes_daily` | 02:30 |
| + invitation expiry, auth/session/PAM cleanup, DB/PAM metrics | — | various |

---

## Open items / deviations introduced by the Zitadel substrate

1. ~~**Recovery codes (MFA-5).**~~ ✅ Resolved — implemented in `accounts/recovery.py` (hashed +
   masked) with `RecoveryCode` model and `v1/me/recovery-codes` routes.
2. **ROPC sunset (F01-1) is trivial** — Zitadel has no Resource Owner Password grant.
3. **Event Listener SPI → Actions V2 webhooks (AUD-3/4).** Native Zitadel auth events are not yet
   captured via an Actions V2 target — only Django-side emit. Confirm coverage.
4. **SCIM maturity (F06).** Confirm Zitadel SCIM vs driving everything via `UserService` v2.
5. **Risk/ACR step-up (MFA-4).** Verify Zitadel honours `acr_values` from `core/risk.py`.
6. **No Terraform.** Old backlog assumed Terraform-managed Keycloak; here config is imperative
   (`scripts/bootstrap_zitadel.py`). Several "via Terraform" stories need a `zitadel/zitadel` IaC
   layer or to be re-scoped to the bootstrap script.
