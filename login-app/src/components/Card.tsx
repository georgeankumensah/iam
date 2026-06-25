import { clsx } from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div
      className={clsx(
        "w-full rounded-[28px] border border-[#f5dfe3] bg-white px-8 py-9 shadow-[0_18px_70px_rgba(203,16,46,0.06)] sm:px-10 sm:py-10",
        className
      )}
    >
      {children}
    </div>
  );
}
