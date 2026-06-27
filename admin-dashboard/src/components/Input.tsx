import type { InputHTMLAttributes } from "react";
import clsx from "../lib/clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, id, className, ...props }: InputProps) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : props.name) || "input";

  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-[13px] font-medium text-[#555]">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={clsx(
          "block h-10 w-full rounded-[7px] border bg-white px-4 text-sm text-[#111111] outline-none transition placeholder:text-[#8a8a8a] disabled:cursor-not-allowed disabled:bg-[#f5f5f5] disabled:text-[#8a8a8a]",
          error ? "border-red-400" : "border-[#d1d5db]",
          className,
        )}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
