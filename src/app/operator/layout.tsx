import OperatorSidebar from "@/components/operator/sidebar";
import OperatorTopbar from "@/components/operator/topbar";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <OperatorSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <OperatorTopbar />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
