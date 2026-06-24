"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/Card";

export default function LogoutPage() {
  const [status, setStatus] = useState("Signing out...");

  useEffect(() => {
    async function doLogout() {
      try {
        await fetch("/api/logout", { method: "POST" });
      } catch {
        // Ignore errors
      }
      setStatus("You have been signed out.");
    }

    doLogout();
  }, []);

  return (
    <Card>
      <div className="text-center">
        <h2 className="mb-2 text-xl font-semibold text-gray-900">Sign out</h2>
        <p className="text-gray-500">{status}</p>
        <a
          href="/loginname"
          className="mt-4 inline-block text-sm text-brand-600 hover:text-brand-500"
        >
          Sign in again
        </a>
      </div>
    </Card>
  );
}
