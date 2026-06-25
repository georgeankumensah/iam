"use client";

import { clsx } from "clsx";
import { forwardRef } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id, className, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : props.name) || "input";

    return (
      <div className="mb-4">
        {label ? (
          <label htmlFor={inputId} className="mb-1.5 block text-[13px] font-medium text-[#555]">
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          className={clsx(
            "block h-10 w-full rounded-[7px] border bg-white px-4 text-sm text-[#111111] shadow-none outline-none transition placeholder:text-[#8a8a8a] focus:ring-0 disabled:cursor-not-allowed disabled:bg-[#f5f5f5] disabled:text-[#8a8a8a]",
            error
              ? "border-red-400 focus:border-red-500"
              : "border-[#d1d5db] focus:border-[#111111]",
            className
          )}
          aria-invalid={error ? "true" : "false"}
          aria-describedby={error ? `${inputId}-error` : undefined}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} className="mt-1 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
