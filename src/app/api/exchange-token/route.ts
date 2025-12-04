import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const token = body.token;
        
        if (!token) {
            return NextResponse.json(
                { success: false, error: 'Token is required' },
                { status: 400 }
            );
        }
        
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
        
        // Get cookies from the incoming request to forward to backend
        const cookies = request.cookies.getAll();
        const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
        
        // Proxy the request to backend
        const response = await fetch(`${backendUrl}/api/exchange-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(cookieHeader && { 'Cookie': cookieHeader }),
            },
            body: JSON.stringify({ token }),
        });
        
        const data = await response.json();
        
        // Forward the response with cookies
        const nextResponse = NextResponse.json(data, { status: response.status });
        
        // Forward Set-Cookie headers from backend to client
        // This ensures the session cookie is set in the browser
        const setCookieHeader = response.headers.get('set-cookie');
        if (setCookieHeader) {
            // Handle multiple Set-Cookie headers
            const setCookieHeaders = response.headers.getSetCookie();
            if (setCookieHeaders && setCookieHeaders.length > 0) {
                setCookieHeaders.forEach(cookie => {
                    nextResponse.headers.append('Set-Cookie', cookie);
                });
            } else {
                // Fallback: use the raw header
                nextResponse.headers.set('Set-Cookie', setCookieHeader);
            }
        }
        
        return nextResponse;
    } catch (error: any) {
        console.error('Token exchange proxy error:', error);
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to exchange token' },
            { status: 500 }
        );
    }
}

export async function OPTIONS() {
    return new NextResponse(null, {
        status: 200,
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        },
    });
}

