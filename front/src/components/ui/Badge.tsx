import { cn } from "@/lib/utils";

type Variant = "green" | "red" | "orange" | "blue" | "gray" | "yellow";

const variants: Record<Variant, string> = {
  green:  "bg-green-100 text-green-800",
  red:    "bg-red-100 text-red-800",
  orange: "bg-orange-100 text-orange-800",
  blue:   "bg-blue-100 text-blue-800",
  gray:   "bg-gray-100 text-gray-700",
  yellow: "bg-yellow-100 text-yellow-800",
};

export function Badge({
  children,
  variant = "gray",
  className,
}: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
