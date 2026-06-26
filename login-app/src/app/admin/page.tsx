"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Copy, LogOut, MailPlus, RefreshCw, RotateCw, Send, ShieldCheck } from "lucide-react";
import { Button } from "@/components/Button";
import { ErrorAlert } from "@/components/ErrorAlert";
import { Input } from "@/components/Input";

type Role = {
  id: string;
  role_id: string;
  name: string;
  is_admin: boolean;
};

type System = {
  system_code: string;
  name: string;
  roles: Role[];
};

type Invitation = {
  id: string;
  email: string;
  system_code: string;
  role_ids: string[];
  zitadel_user_id: string;
  status: string;
  invite_code?: string;
  lookup_token?: string;
  created_at: string;
};

export default function AdminPage() {
  const [systems, setSystems] = useState<System[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [selectedSystem, setSelectedSystem] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<Invitation | null>(null);
  const [copied, setCopied] = useState(false);
  const [origin, setOrigin] = useState("");
  const [resendingId, setResendingId] = useState<string | null>(null);

  const activeSystem = useMemo(
    () => systems.find((system) => system.system_code === selectedSystem),
    [selectedSystem, systems]
  );

  const inviteLink = created?.invite_code
    ? `${origin}/invite?t=${encodeURIComponent(created.lookup_token || "")}&code=${encodeURIComponent(created.invite_code)}`
    : "";

  useEffect(() => {
    setOrigin(window.location.origin);
    void load();
  }, []);

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const [systemsResp, invitationsResp] = await Promise.all([
        fetch("/api/admin/systems", { cache: "no-store" }),
        fetch("/api/admin/invitations", { cache: "no-store" }),
      ]);
      if (!systemsResp.ok) throw new Error("Sign in as a superadmin to manage invitations");
      const systemsData = await systemsResp.json();
      const invitationData = invitationsResp.ok ? await invitationsResp.json() : { data: [] };
      const nextSystems = systemsData.data || [];
      setSystems(nextSystems);
      setInvitations(invitationData.data || []);
      if (!selectedSystem && nextSystems[0]) setSelectedSystem(nextSystems[0].system_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load admin console");
    } finally {
      setLoading(false);
    }
  }

  function toggleRole(roleId: string) {
    setSelectedRoles((current) =>
      current.includes(roleId) ? current.filter((id) => id !== roleId) : [...current, roleId]
    );
  }

  async function createInvitation(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setCreated(null);
    setCopied(false);

    if (!firstName.trim()) {
      setError("Enter a first name");
      return;
    }
    if (!lastName.trim()) {
      setError("Enter a last name");
      return;
    }
    if (!email.trim()) {
      setError("Enter an email address");
      return;
    }
    if (!selectedSystem || selectedRoles.length === 0) {
      setError("Choose a system and at least one role");
      return;
    }

    setSubmitting(true);
    try {
      const resp = await fetch("/api/admin/invitations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email,
          system_code: selectedSystem,
          role_ids: selectedRoles,
        }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        throw new Error(data.message || data.error || "Could not create invitation");
      }
      setCreated(data.data);
      setFirstName("");
      setLastName("");
      setEmail("");
      setSelectedRoles([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create invitation");
    } finally {
      setSubmitting(false);
    }
  }

  async function copyInviteLink() {
    if (!created?.invite_code) return;
    const text = `User: ${created.email}\nCode: ${created.invite_code}\nLink: ${inviteLink}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  async function resendInvitation(invitation: Invitation) {
    setError(null);
    setCreated(null);
    setCopied(false);
    setResendingId(invitation.id);
    try {
      const resp = await fetch(`/api/admin/invitations/${invitation.id}/resend`, {
        method: "POST",
      });
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        throw new Error(data.message || data.error || "Could not resend invitation");
      }
      setCreated(data.data);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend invitation");
    } finally {
      setResendingId(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#f4f6f2] text-[#18211d]">
      <header className="border-b border-[#d8ded3] bg-[#101915] text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#d6ff6b] text-[#101915]">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-wide">CLET IAM Control</h1>
              <p className="text-xs text-[#aeb9b2]">System invitations and role grants</p>
            </div>
          </div>
          <a
            href="/admin/users"
            className="inline-flex items-center gap-2 rounded-md border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/10"
          >
            <ShieldCheck size={16} />
            Users
          </a>
          <a
            href="/logout"
            className="inline-flex items-center gap-2 rounded-md border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/10"
          >
            <LogOut size={16} />
            Sign out
          </a>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-lg border border-[#d8ded3] bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">Invite a user</h2>
              <p className="mt-1 text-sm text-[#667267]">
                Pick a system, grant roles, then use the returned invite code to test onboarding.
              </p>
            </div>
            <button
              type="button"
              onClick={load}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[#d8ded3] text-[#4a554d] hover:bg-[#f4f6f2]"
              aria-label="Refresh"
            >
              <RefreshCw size={16} />
            </button>
          </div>

          <ErrorAlert message={error} className="mb-4" />

          {loading ? (
            <div className="rounded-md border border-[#d8ded3] bg-[#f9faf7] px-4 py-8 text-center text-sm text-[#667267]">
              Loading admin console...
            </div>
          ) : (
            <form onSubmit={createInvitation} className="grid gap-5">
              <div className="grid gap-5 sm:grid-cols-2">
                <Input
                  label="First name"
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  placeholder="Jane"
                  autoComplete="given-name"
                />
                <Input
                  label="Last name"
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  placeholder="Doe"
                  autoComplete="family-name"
                />
              </div>

              <Input
                label="Invitee email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="person@clet.gov.gh"
                autoComplete="email"
              />

              <div>
                <label htmlFor="system" className="mb-1 block text-sm font-medium text-gray-700">
                  System
                </label>
                <select
                  id="system"
                  value={selectedSystem}
                  onChange={(event) => {
                    setSelectedSystem(event.target.value);
                    setSelectedRoles([]);
                  }}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {systems.map((system) => (
                    <option key={system.system_code} value={system.system_code}>
                      {system.name} ({system.system_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-700">Roles</h3>
                  <span className="text-xs text-[#667267]">{selectedRoles.length} selected</span>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  {(activeSystem?.roles || []).map((role) => {
                    const checked = selectedRoles.includes(role.id);
                    return (
                      <button
                        type="button"
                        key={role.id}
                        onClick={() => toggleRole(role.id)}
                        className={`flex min-h-16 items-center justify-between rounded-md border px-3 py-2 text-left transition ${
                          checked
                            ? "border-[#4d6b2f] bg-[#eff8d5]"
                            : "border-[#d8ded3] bg-white hover:bg-[#f9faf7]"
                        }`}
                      >
                        <span>
                          <span className="block text-sm font-medium">{role.name}</span>
                          <span className="block text-xs text-[#667267]">
                            {role.role_id}{role.is_admin ? " / admin" : ""}
                          </span>
                        </span>
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded border ${
                            checked ? "border-[#4d6b2f] bg-[#4d6b2f] text-white" : "border-[#c9d0c5]"
                          }`}
                        >
                          {checked ? <Check size={14} /> : null}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <Button type="submit" loading={submitting} fullWidth={false} className="w-fit gap-2 px-5">
                <Send size={16} />
                Create invitation
              </Button>
            </form>
          )}

          {created ? (
            <div className="mt-6 rounded-lg border border-[#bfd184] bg-[#f7fbeb] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#31441d]">
                <MailPlus size={16} />
                Invitation ready
              </div>
              <div className="grid gap-2 text-sm">
                <div>
                  <span className="text-[#667267]">Email:</span> {created.email}
                </div>
                <div>
                  <span className="text-[#667267]">Code:</span>{" "}
                  <code className="rounded bg-white px-2 py-1 font-mono">{created.invite_code}</code>
                </div>
              </div>
              <button
                type="button"
                onClick={copyInviteLink}
                className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#101915] px-3 py-2 text-sm text-white hover:bg-[#26322c]"
              >
                <Copy size={15} />
                {copied ? "Copied" : "Copy test details"}
              </button>
            </div>
          ) : null}
        </section>

        <aside className="rounded-lg border border-[#d8ded3] bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#667267]">Recent invitations</h2>
          <div className="mt-4 grid gap-3">
            {invitations.length === 0 ? (
              <div className="rounded-md border border-dashed border-[#d8ded3] px-3 py-6 text-center text-sm text-[#667267]">
                No invitations yet.
              </div>
            ) : (
              invitations.map((invitation) => (
                <div key={invitation.id} className="rounded-md border border-[#e1e6dd] p-3">
                  <div className="truncate text-sm font-medium">{invitation.email}</div>
                  <div className="mt-1 flex items-center justify-between text-xs text-[#667267]">
                    <span>{invitation.system_code}</span>
                    <span className="rounded bg-[#f4f6f2] px-2 py-1">{invitation.status}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => resendInvitation(invitation)}
                    disabled={resendingId === invitation.id}
                    className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-[#d8ded3] px-3 py-2 text-xs font-medium text-[#31441d] hover:bg-[#f4f6f2] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <RotateCw size={13} className={resendingId === invitation.id ? "animate-spin" : ""} />
                    Resend invite
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
