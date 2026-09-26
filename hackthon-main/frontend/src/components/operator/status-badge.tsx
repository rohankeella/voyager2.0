import { cn } from "@/lib/utils";

const styles: Record<string, string> = {
  // booking status
  pending: "bg-amber-100 text-amber-700",
  confirmed: "bg-blue-100 text-blue-700",
  "in-progress": "bg-primary/10 text-primary",
  completed: "bg-purple-100 text-purple-700",
  cancelled: "bg-red-100 text-red-700",
  // payment status
  unpaid: "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
  paid: "bg-emerald-100 text-emerald-700",
  refunded: "bg-gray-100 text-gray-600",
  // vendor / group status
  active: "bg-emerald-100 text-emerald-700",
  inactive: "bg-gray-100 text-gray-500",
  forming: "bg-amber-100 text-amber-700",
  // change request status
  open: "bg-red-100 text-red-700",
  reviewing: "bg-amber-100 text-amber-700",
  resolved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-gray-100 text-gray-500",
  // payment record status
  success: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold capitalize",
        styles[status] ?? "bg-gray-100 text-gray-600"
      )}
    >
      {status.replace("-", " ")}
    </span>
  );
}
