import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function WarmupPage() {
    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Email Warmup</h1>
                <p className="text-muted-foreground">
                    Monitor your email warmup progress
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Warmup Status</CardTitle>
                    <CardDescription>Email account warmup metrics</CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">Warmup dashboard coming soon...</p>
                </CardContent>
            </Card>
        </div>
    );
}
