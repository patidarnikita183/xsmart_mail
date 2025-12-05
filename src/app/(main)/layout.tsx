import { AppLayout } from "@/components/Layout/AppLayout";

export const dynamic = 'force-dynamic';

export default function MainLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <AppLayout>{children}</AppLayout>;
}
