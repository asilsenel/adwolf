import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-cream-light flex">
            <Sidebar />
            <main className="flex-1 lg:ml-0 overflow-auto">
                {children}
            </main>
        </div>
    );
}
