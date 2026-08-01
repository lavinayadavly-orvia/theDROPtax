export default {
    async fetch(request, env) {
        let url = new URL(request.url);
        let path = url.pathname;

        // ==========================================
        // API PROXY ROUTING
        // All /api/* calls are forwarded directly to the Render Python Backend
        // ==========================================
        if (path.startsWith('/api/')) {
            const normalizedPath = path.replace(/\/$/, ''); // Remove trailing slash

            // Health check
            if (normalizedPath === '/api/health') {
                return new Response(JSON.stringify({
                    status: 'ok',
                    msg: 'DROP Tax edge proxy active',
                    time: new Date().toISOString()
                }), {
                    status: 200,
                    headers: {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                });
            }

            // --- THE TRUE PROXY ---
            // Forward everything else to the backend. Set BACKEND_URL as a
            // Cloudflare Pages environment variable so infrastructure moves do
            // not require a code change + rebuild.
            const BACKEND_URL = env?.BACKEND_URL;
            if (!BACKEND_URL) {
                return new Response(JSON.stringify({ error: "BACKEND_URL is not configured for this deployment." }),
                    { status: 503, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
            }
            const targetUrl = new URL(request.url);
            targetUrl.hostname = new URL(BACKEND_URL).hostname;
            targetUrl.protocol = 'https:';
            targetUrl.port = ''; // Clear any local port

            try {
                // Ensure CORS headers are injected on the prepflight
                if (request.method === 'OPTIONS') {
                    return new Response(null, {
                        headers: {
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                        }
                    });
                }

                // Create clean headers to prevent Render from rejecting Cloudflare's internal proxy headers
                const cleanHeaders = new Headers();
                cleanHeaders.set('Accept', '*/*');
                cleanHeaders.set('User-Agent', request.headers.get('User-Agent') || 'Cloudflare-Worker-Proxy');
                if (request.method !== 'GET' && request.method !== 'HEAD') {
                    const contentType = request.headers.get('Content-Type');
                    if (contentType) cleanHeaders.set('Content-Type', contentType);
                }

                // Proxy the actual request without passing through all original Cloudflare headers
                let proxyRequest = new Request(targetUrl.toString(), {
                    method: request.method,
                    headers: cleanHeaders,
                    body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
                    redirect: 'manual'
                });

                const backendResponse = await fetch(proxyRequest);

                // Return the backend's response but ensure CORS is attached
                const response = new Response(backendResponse.body, backendResponse);
                response.headers.set('Access-Control-Allow-Origin', '*');
                return response;

            } catch (err) {
                return new Response(JSON.stringify({
                    error: "Proxy to Intelligence Backend failed",
                    details: err.message
                }), {
                    status: 502,
                    headers: {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                });
            }
        }

        // Static Asset Handling
        // env.ASSETS is provided by Cloudflare Pages to fetch the uploaded static files
        const response = await env.ASSETS.fetch(request);

        // If static file not found (404), serve index.html for SPA routing
        if (response.status === 404 && !path.startsWith('/static/')) {
            return env.ASSETS.fetch(new Request(`${url.origin}/index.html`));
        }

        return response;
    }
};
