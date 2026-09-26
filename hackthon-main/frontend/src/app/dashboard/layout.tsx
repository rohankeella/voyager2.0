import Sidebar from "@/components/dashboard/sidebar";
import Topbar from "@/components/dashboard/topbar";
import BackButton from "@/components/ui/back-button";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar userName="Rohan" />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8"><BackButton fallbackHref="/discover" />{children}</main>
      </div>
    </div>
  );
}
