import { LogOut, ShieldCheck } from "lucide-react";

export function LogoutDone() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f4f6f2]">
      <div className="w-full max-w-sm rounded-lg border border-[#d8ded3] bg-white p-8 shadow-sm text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#f4f6f2]">
          <LogOut size={24} className="text-[#667267]" />
        </div>
        <h1 className="text-lg font-semibold text-[#18211d]">Signed out</h1>
        <p className="mt-2 text-sm text-[#667267]">
          You have been signed out of the admin dashboard.
        </p>
        <a
          href="/login"
          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#18211d] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#2a362f]"
        >
          <ShieldCheck size={16} />
          Sign in again
        </a>
      </div>
    </main>
  );
}
