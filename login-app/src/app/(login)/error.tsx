"use client";

export default function LoginError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-lg bg-white p-8 shadow-md">
      <h2 className="mb-4 text-xl font-semibold text-red-600">Authentication Error</h2>
      <p className="mb-6 text-gray-600">
        {error.message || "An error occurred during authentication. Please try again."}
      </p>
      <button
        onClick={reset}
        className="w-full rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
      >
        Try again
      </button>
    </div>
  );
}
