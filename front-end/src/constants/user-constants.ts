// time in ms between login status checks for authentication status
export const LOGIN_STATUS_CHECK_INTERVAL = 10000;

// multiply by status check interval to calculate "max" time we will poll the server
// 60 * 10000 = 10 minutes
export const MAX_LOGIN_CHECK_ATTEMPTS = 60;

export const STRIPE_LIB_URL = 'https://js.stripe.com/v3/';
