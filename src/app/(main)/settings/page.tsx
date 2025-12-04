import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SettingsPage() {
    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground">
                    Manage your account settings and preferences
                </p>
            </div>

            <Tabs defaultValue="profile" className="w-full">
                <TabsList>
                    <TabsTrigger value="profile">Profile</TabsTrigger>
                    <TabsTrigger value="team">Team</TabsTrigger>
                    <TabsTrigger value="billing">Billing</TabsTrigger>
                    <TabsTrigger value="api">API Keys</TabsTrigger>
                </TabsList>
                <TabsContent value="profile" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Profile Settings</CardTitle>
                            <CardDescription>Manage your profile information</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground">Profile settings coming soon...</p>
                        </CardContent>
                    </Card>
                </TabsContent>
                <TabsContent value="team" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Team Members</CardTitle>
                            <CardDescription>Manage your team members</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground">Team management coming soon...</p>
                        </CardContent>
                    </Card>
                </TabsContent>
                <TabsContent value="billing" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Billing</CardTitle>
                            <CardDescription>Manage your subscription and billing</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground">Billing settings coming soon...</p>
                        </CardContent>
                    </Card>
                </TabsContent>
                <TabsContent value="api" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>API Keys</CardTitle>
                            <CardDescription>Manage your API keys</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground">API key management coming soon...</p>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
