"use client";

import { clsx } from "clsx";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  loading?: boolean;
  fullWidth?: boolean;
}

export function Button({
  variant = "primary",
  loading = false,
  fullWidth = true,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "flex h-9 items-center justify-center gap-2 whitespace-nowrap rounded-[7px] px-3 text-[12px] font-medium shadow-none outline-none transition focus:outline-none focus:ring-0 disabled:cursor-not-allowed disabled:opacity-70",
        fullWidth && "w-full",
        variant === "primary" && "border-0 bg-[#111111] text-white hover:bg-black disabled:bg-[#8c8c8c]",
        variant === "secondary" && "border border-[#d1d5db] bg-white text-[#111111] hover:bg-[#f8f8f8] disabled:bg-[#f3f4f6] disabled:text-[#8c8c8c]",
        variant === "danger" && "border-0 bg-red-600 text-white hover:bg-red-700 disabled:bg-[#8c8c8c]",
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : null}
      {children}
    </button>
  );
}
