export const formatLargeCurrency = (value, currencySymbol) => {
    if (value === null || value === undefined) return '0';

    // Convert to number if it's a string
    const num = Number(value);
    if (isNaN(num)) return '0';

    // Handle Indian Rupees (INR) which uses Lakhs (100,000) and Crores (10,000,000)
    if (currencySymbol === '₹') {
        if (num >= 10000000) {
            return `${currencySymbol}${(num / 10000000).toFixed(2)} Cr`;
        } else if (num >= 100000) {
            return `${currencySymbol}${(num / 100000).toFixed(2)} L`;
        } else if (num >= 1000) {
            return `${currencySymbol}${(num / 1000).toFixed(1)}k`;
        }
        return `${currencySymbol}${num.toLocaleString('en-IN')}`;
    }

    // Handle standard Western formatting (USD, EUR, GBP) using Millions and Billions
    if (num >= 1000000000) {
        return `${currencySymbol}${(num / 1000000000).toFixed(2)}B`;
    } else if (num >= 1000000) {
        return `${currencySymbol}${(num / 1000000).toFixed(2)}M`;
    } else if (num >= 1000) {
        return `${currencySymbol}${(num / 1000).toFixed(1)}k`;
    }

    return `${currencySymbol}${num.toLocaleString()}`;
};
