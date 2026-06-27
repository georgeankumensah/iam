import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "../lib/clsx";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export function Button({ className, children, ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md bg-[#18211d] px-4 py-2 text-sm font-medium text-white hover:bg-[#2a362f] disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
