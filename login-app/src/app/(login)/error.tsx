"use client";

import { Card } from "@/components/Card";
import { Button } from "@/components/Button";

export default function LoginError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <Card>
      <h1 className="text-center text-[22px] font-bold text-red-600">Authentication Error</h1>
      <p className="mx-auto my-6 max-w-[420px] text-center text-[15px] leading-6 text-[#777]">
        {error.message || "An error occurred during authentication. Please try again."}
      </p>
      <Button onClick={reset}>
        Try again
      </Button>
    </Card>
  );
}
