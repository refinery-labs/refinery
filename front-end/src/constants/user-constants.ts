// time in ms between login status checks for authentication status
export const LOGIN_STATUS_CHECK_INTERVAL = 5000;

// multiply by status check interval to calculate "max" time we will poll the server
// 120 * 5000 = 10 minutes
export const MAX_LOGIN_CHECK_ATTEMPTS = 120;
