"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface AnalyticsChartProps {
    data: Array<{
        date: string;
        sent: number;
        opened: number;
        clicked: number;
        bounced: number;
    }>;
}

export default function AnalyticsChart({ data }: AnalyticsChartProps) {
    // Format date for display
    const formattedData = data.map(item => ({
        ...item,
        displayDate: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }));

    return (
        <Card className="shadow-md border-0">
            <CardHeader>
                <CardTitle className="text-xl font-semibold text-gray-800">
                    Performance Trends (Last 30 Days)
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                    Track your email campaign performance over time
                </p>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={formattedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorSent" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorOpened" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorClicked" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorBounced" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                            dataKey="displayDate"
                            stroke="#6b7280"
                            fontSize={12}
                            tickLine={false}
                        />
                        <YAxis
                            stroke="#6b7280"
                            fontSize={12}
                            tickLine={false}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'white',
                                border: '1px solid #e5e7eb',
                                borderRadius: '8px',
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                            }}
                            labelStyle={{ color: '#374151', fontWeight: 600 }}
                        />
                        <Legend
                            wrapperStyle={{ paddingTop: '20px' }}
                            iconType="circle"
                        />
                        <Area
                            type="monotone"
                            dataKey="sent"
                            stroke="#3b82f6"
                            fillOpacity={1}
                            fill="url(#colorSent)"
                            strokeWidth={2}
                            name="Sent"
                        />
                        <Area
                            type="monotone"
                            dataKey="opened"
                            stroke="#10b981"
                            fillOpacity={1}
                            fill="url(#colorOpened)"
                            strokeWidth={2}
                            name="Opened"
                        />
                        <Area
                            type="monotone"
                            dataKey="clicked"
                            stroke="#8b5cf6"
                            fillOpacity={1}
                            fill="url(#colorClicked)"
                            strokeWidth={2}
                            name="Clicked"
                        />
                        <Area
                            type="monotone"
                            dataKey="bounced"
                            stroke="#ef4444"
                            fillOpacity={1}
                            fill="url(#colorBounced)"
                            strokeWidth={2}
                            name="Bounced"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
