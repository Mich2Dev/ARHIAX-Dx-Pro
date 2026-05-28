import { cn } from "@/lib/utils";

type Color = "blue" | "orange" | "green" | "red";

const colors: Record<Color, string> = {
  blue:   "bg-blue-50 text-blue-700 border-blue-100",
  orange: "bg-orange-50 text-orange-700 border-orange-100",
  green:  "bg-green-50 text-green-700 border-green-100",
  red:    "bg-red-50 text-red-700 border-red-100",
};

export function StatsCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: Color;
}) {
  return (
    <div className={cn("rounded-xl border p-4", colors[color])}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs font-medium mt-1 opacity-80">{label}</p>
    </div>
  );
}
