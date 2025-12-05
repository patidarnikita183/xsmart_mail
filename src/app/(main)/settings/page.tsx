"use client";

import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ProfileAvatar } from "@/components/Profile/ProfileAvatar";
import { toast } from "@/components/ui/use-toast";
import { Loader2, Mail, User } from "lucide-react";

export default function SettingsPage() {
    const { user, isLoaded } = useUser();
    const [firstName, setFirstName] = useState(user?.firstName || "");
    const [lastName, setLastName] = useState(user?.lastName || "");
    const [isSaving, setIsSaving] = useState(false);

    const hasChanges =
        firstName !== (user?.firstName || "") ||
        lastName !== (user?.lastName || "");

    const handleSave = async () => {
        if (!user) return;

        try {
            setIsSaving(true);
            await user.update({
                firstName: firstName || undefined,
                lastName: lastName || undefined,
            });
            await user.reload(); // Refresh user data to update name everywhere

            toast({
                title: "Success",
                description: "Profile updated successfully!",
            });
        } catch (error) {
            console.error("Error updating profile:", error);
            toast({
                title: "Error",
                description: "Failed to update profile. Please try again.",
                variant: "destructive",
            });
        } finally {
            setIsSaving(false);
        }
    };

    if (!isLoaded) {
        return (
            <div className="flex items-center justify-center h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6 max-w-4xl">
            <div>
                <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Settings</h1>
                <p className="text-muted-foreground mt-1">
                    Manage your account settings and preferences
                </p>
            </div>

            <Tabs defaultValue="profile" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="profile">Profile</TabsTrigger>
                    <TabsTrigger value="team">Team</TabsTrigger>
                    <TabsTrigger value="billing">Billing</TabsTrigger>
                    <TabsTrigger value="api">API Keys</TabsTrigger>
                </TabsList>

                <TabsContent value="profile" className="mt-6 space-y-6">
                    {/* Avatar Section */}
                    <Card className="border-0 shadow-lg">
                        <CardHeader>
                            <CardTitle>Profile Picture</CardTitle>
                            <CardDescription>Upload a custom avatar or choose from our gallery</CardDescription>
                        </CardHeader>
                        <CardContent className="flex justify-center py-6">
                            <ProfileAvatar />
                        </CardContent>
                    </Card>

                    {/* Personal Information */}
                    <Card className="border-0 shadow-lg">
                        <CardHeader>
                            <CardTitle>Personal Information</CardTitle>
                            <CardDescription>Update your personal details</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <Label htmlFor="firstName" className="flex items-center gap-2">
                                        <User className="h-4 w-4 text-muted-foreground" />
                                        First Name
                                    </Label>
                                    <Input
                                        id="firstName"
                                        value={firstName}
                                        onChange={(e) => setFirstName(e.target.value)}
                                        placeholder="Enter your first name"
                                        className="transition-all focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="lastName" className="flex items-center gap-2">
                                        <User className="h-4 w-4 text-muted-foreground" />
                                        Last Name
                                    </Label>
                                    <Input
                                        id="lastName"
                                        value={lastName}
                                        onChange={(e) => setLastName(e.target.value)}
                                        placeholder="Enter your last name"
                                        className="transition-all focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="email" className="flex items-center gap-2">
                                    <Mail className="h-4 w-4 text-muted-foreground" />
                                    Email Address
                                </Label>
                                <Input
                                    id="email"
                                    value={user?.primaryEmailAddress?.emailAddress || ""}
                                    disabled
                                    className="bg-gray-50 cursor-not-allowed"
                                />
                                <p className="text-xs text-muted-foreground">
                                    Email address cannot be changed here. Please contact support if needed.
                                </p>
                            </div>

                            <div className="flex justify-end pt-4 border-t">
                                <Button
                                    onClick={handleSave}
                                    disabled={!hasChanges || isSaving}
                                    className="shadow-lg hover:shadow-xl transition-all"
                                >
                                    {isSaving ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Saving...
                                        </>
                                    ) : (
                                        "Save Changes"
                                    )}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="team" className="mt-6">
                    <Card className="border-0 shadow-lg">
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
                    <Card className="border-0 shadow-lg">
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
                    <Card className="border-0 shadow-lg">
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
