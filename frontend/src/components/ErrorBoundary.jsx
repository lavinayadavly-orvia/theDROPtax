import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Uncaught error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-[#0B1120] text-white p-8">
                    <div className="max-w-md w-full space-y-4 text-center">
                        <h1 className="text-2xl font-bold text-red-500">Something went wrong</h1>
                        <p className="text-gray-400">
                            The application encountered an unexpected error. Please try refreshing the page.
                        </p>
                        <pre className="p-4 bg-black/50 rounded text-xs text-left overflow-auto max-h-48 text-red-400/80 font-mono">
                            {this.state.error?.toString()}
                        </pre>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-6 py-2 bg-[#008080] hover:bg-[#00A0A0] rounded transition-colors"
                        >
                            Refresh Page
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
