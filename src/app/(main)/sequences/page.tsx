import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function SequencesPage() {
    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Sequences</h1>
                    <p className="text-muted-foreground">
                        Create and manage email sequences
                    </p>
                </div>
                <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    New Sequence
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Email Sequences</CardTitle>
                    <CardDescription>
                        Build multi-step email sequences with delays and personalization
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">No sequences created yet. Click "New Sequence" to get started.</p>
                </CardContent>
            </Card>
        </div>
    );
}
