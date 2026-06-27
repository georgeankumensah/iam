import { useCallback, useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  LogOut,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Trash2,
  Users as UsersIcon,
  XCircle,
} from "lucide-react";
import { useAuth } from "@rfdtech/oidc-client/react";
import { Button } from "../components/Button";
import { ErrorAlert } from "../components/ErrorAlert";
import { Input } from "../components/Input";
import { useApi } from "../api/client";

interface UserRecord {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  user_type: string;
  status: string;
  created_at: string;
}

const STATUS_LABELS: Record<string, string> = {
  pre_active: "Pre-active",
  active: "Active",
  disabled: "Disabled",
  pending: "Pending",
};

const TYPE_LABELS: Record<string, string> = {
  staff: "Staff",
  board: "Board",
  nbec: "NBEC",
  student: "Student",
  external: "External",
  public: "Public",
};

export function Users() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reactivatingId, setReactivatingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const { logout } = useAuth();
  const api = useApi();

  const load = useCallback(
    async (p: number, q: string) => {
      setError(null);
      setLoading(true);
      try {
        const params = new URLSearchParams({ page: String(p), page_size: "50" });
        if (q.trim()) params.set("search", q.trim());
        const resp = await api.get<{ data: UserRecord[]; meta: { total: number } }>(
          `/v1/admin/users?${params}`,
        );
        if (resp.status !== 200) throw new Error("Sign in as a superadmin to manage users");
        setUsers(resp.data.data || []);
        setTotal(resp.data.meta?.total || 0);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load users");
      } finally {
        setLoading(false);
      }
    },
    [api],
  );

  useEffect(() => {
    void load(page, search);
  }, [page, load]);

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    void load(1, search);
  }

  function totalPages() {
    return Math.max(1, Math.ceil(total / pageSize));
  }

  async function handleDelete(user: UserRecord) {
    setError(null);
    setDeletingId(user.id);
    try {
      const resp = await api.del<{ success: boolean; error?: string }>(
        `/v1/admin/users/${user.id}`,
      );
      if (resp.status !== 200 || !resp.data.success) {
        throw new Error(resp.data.error || "Could not delete user");
      }
      setConfirmId(null);
      await load(page, search);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete user");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleReactivate(user: UserRecord) {
    setError(null);
    setReactivatingId(user.id);
    try {
      const resp = await api.post<{ success: boolean; error?: string }>(
        `/v1/admin/users/${user.id}/reactivate`,
      );
      if (resp.status !== 200 || !resp.data.success) {
        throw new Error(resp.data.error || "Could not reactivate user");
      }
      await load(page, search);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reactivate user");
    } finally {
      setReactivatingId(null);
    }
  }

  function userName(user: UserRecord) {
    return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
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
              <p className="text-xs text-[#aeb9b2]">User management</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => { window.location.href = "/"; }}
              className="inline-flex items-center gap-2 rounded-md border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/10"
            >
              <ChevronLeft size={16} />
              Invitations
            </button>
            <button
              type="button"
              onClick={() => logout({ prompt: "none" })}
              className="inline-flex items-center gap-2 rounded-md border border-white/15 px-3 py-2 text-sm text-white hover:bg-white/10"
            >
              <LogOut size={16} />
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-6">
        <section className="rounded-lg border border-[#d8ded3] bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">
                <UsersIcon size={20} className="mr-2 inline-block align-text-top" />
                Users
              </h2>
              <p className="mt-1 text-sm text-[#667267]">{total} total user(s)</p>
            </div>
            <div className="flex items-center gap-3">
              <form onSubmit={handleSearch} className="flex items-center gap-2">
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search name or email…"
                  className="w-56"
                />
                <Button type="submit" className="gap-1">
                  <Search size={14} />
                  Search
                </Button>
              </form>
              <button
                type="button"
                onClick={() => load(page, search)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[#d8ded3] text-[#4a554d] hover:bg-[#f4f6f2]"
                aria-label="Refresh"
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>

          <ErrorAlert message={error} className="mb-4" />

          {loading ? (
            <div className="rounded-md border border-[#d8ded3] bg-[#f9faf7] px-4 py-12 text-center text-sm text-[#667267]">
              Loading users…
            </div>
          ) : users.length === 0 ? (
            <div className="rounded-md border border-dashed border-[#d8ded3] px-4 py-12 text-center text-sm text-[#667267]">
              {search ? "No users match your search." : "No users found."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#e1e6dd] text-xs uppercase tracking-wide text-[#667267]">
                    <th className="py-3 pr-4 font-medium">Name</th>
                    <th className="py-3 pr-4 font-medium">Email</th>
                    <th className="py-3 pr-4 font-medium">Type</th>
                    <th className="py-3 pr-4 font-medium">Status</th>
                    <th className="py-3 pr-4 font-medium">Created</th>
                    <th className="py-3 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-b border-[#f4f6f2] hover:bg-[#f9faf7]">
                      <td className="py-3 pr-4 font-medium">{userName(user)}</td>
                      <td className="py-3 pr-4 text-[#667267]">{user.email}</td>
                      <td className="py-3 pr-4">
                        <span className="rounded bg-[#f4f6f2] px-2 py-1 text-xs">
                          {TYPE_LABELS[user.user_type] || user.user_type}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`rounded px-2 py-1 text-xs ${
                            user.status === "active"
                              ? "bg-[#dff0d8] text-[#2d5a27]"
                              : user.status === "disabled"
                              ? "bg-[#f2dede] text-[#8b3a3a]"
                              : "bg-[#fcf8e3] text-[#8a6d3b]"
                          }`}
                        >
                          {STATUS_LABELS[user.status] || user.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-xs text-[#667267]">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 text-right">
                        {user.status === "disabled" ? (
                          <button
                            type="button"
                            onClick={() => handleReactivate(user)}
                            disabled={reactivatingId === user.id}
                            className="inline-flex items-center gap-1 rounded border border-[#d8ded3] px-3 py-1.5 text-xs font-medium text-[#2d5a27] hover:bg-[#dff0d8] disabled:opacity-50"
                          >
                            <RotateCcw size={13} />
                            {reactivatingId === user.id ? "Reactivating…" : "Reactivate"}
                          </button>
                        ) : confirmId === user.id ? (
                          <div className="inline-flex items-center gap-2">
                            <span className="text-xs text-[#8b3a3a]">Delete?</span>
                            <button
                              type="button"
                              onClick={() => handleDelete(user)}
                              disabled={deletingId === user.id}
                              className="inline-flex items-center gap-1 rounded bg-[#8b3a3a] px-2 py-1 text-xs font-medium text-white hover:bg-[#6b2a2a] disabled:opacity-50"
                            >
                              {deletingId === user.id ? "Deleting…" : "Confirm"}
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmId(null)}
                              className="inline-flex items-center gap-1 rounded border border-[#d8ded3] px-2 py-1 text-xs text-[#4a554d] hover:bg-[#f4f6f2]"
                            >
                              <XCircle size={12} />
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmId(user.id)}
                            className="inline-flex items-center gap-1 rounded border border-[#d8ded3] px-3 py-1.5 text-xs font-medium text-[#8b3a3a] hover:bg-[#fef2f2] disabled:opacity-50"
                          >
                            <Trash2 size={13} />
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {total > pageSize && (
            <div className="mt-5 flex items-center justify-between border-t border-[#e1e6dd] pt-4 text-sm text-[#667267]">
              <span>
                Page {page} of {totalPages()} ({total} total)
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 rounded border border-[#d8ded3] px-3 py-1.5 text-xs hover:bg-[#f4f6f2] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft size={14} />
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= totalPages()}
                  className="inline-flex items-center gap-1 rounded border border-[#d8ded3] px-3 py-1.5 text-xs hover:bg-[#f4f6f2] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
