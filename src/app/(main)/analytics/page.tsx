import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
                <p className="text-muted-foreground">
                    Track your email performance and metrics
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Delivery Rate</CardTitle>
                        <CardDescription>Email delivery performance</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">98.5%</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader>
                        <CardTitle>Bounce Rate</CardTitle>
                        <CardDescription>Email bounce statistics</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">1.5%</div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
