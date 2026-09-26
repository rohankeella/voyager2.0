import { seedCoordinators, seedGroups } from "@/lib/operator-data";
import { Mail, Phone, MapPin } from "lucide-react";

export default function OperatorCoordinatorsPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-bold text-dark">Coordinators</h1>
      <p className="mt-1 text-sm text-gray-500">The field team keeping each tour group running smoothly.</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {seedCoordinators.map((c) => {
          const groups = seedGroups.filter((g) => g.coordinatorId === c.id);
          return (
            <div key={c.id} className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
              <p className="font-semibold text-dark">{c.name}</p>
              <p className="mt-1 flex items-center gap-1.5 text-xs text-gray-500">
                <MapPin className="h-3.5 w-3.5" /> {c.region}
              </p>
              <p className="mt-2 flex items-center gap-1.5 text-xs text-gray-500">
                <Mail className="h-3.5 w-3.5" /> {c.email}
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-xs text-gray-500">
                <Phone className="h-3.5 w-3.5" /> {c.phone}
              </p>
              <div className="mt-3 border-t border-gray-50 pt-3 text-xs text-gray-500">
                Managing <span className="font-semibold text-dark">{groups.length}</span> group{groups.length === 1 ? "" : "s"}
                {groups.length > 0 && `: ${groups.map((g) => g.destination).join(", ")}`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
