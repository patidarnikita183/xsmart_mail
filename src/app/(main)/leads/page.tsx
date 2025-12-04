import { LeadsTable } from "@/components/Leads/LeadsTable";
import { Button } from "@/components/ui/button";
import { Plus, Upload } from "lucide-react";

export default function LeadsPage() {
    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Lead Manager</h1>
                    <p className="text-muted-foreground">
                        Manage your leads and contacts
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline">
                        <Upload className="mr-2 h-4 w-4" />
                        Import CSV
                    </Button>
                    <Button>
                        <Plus className="mr-2 h-4 w-4" />
                        Add Lead
                    </Button>
                </div>
            </div>

            <LeadsTable />
        </div>
    );
}
