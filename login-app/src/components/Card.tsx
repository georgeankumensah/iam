import { clsx } from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={clsx("rounded-lg bg-white px-6 py-8 shadow-md", className)}>
      {children}
    </div>
  );
}
