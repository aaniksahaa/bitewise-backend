# Authentication Updates: Relaxed OTP Verification

## Overview

The authentication system has been updated to make email OTP verification more user-friendly by introducing a time-based threshold for requiring OTP verification during login.

## Changes Made

### 1. Database Schema Updates

- **Added `last_login_at` field** to the `users` table to track when users last successfully logged in
- **Created migration** `add_last_login_at_to_users` to add this field to existing databases

### 2. Smart OTP Requirement Logic

The system now intelligently decides when to require OTP verification based on:

- **First-time users**: Always require OTP verification
- **Recent users**: If last login was within the threshold (default: 7 days), skip OTP and provide tokens directly
- **Inactive users**: If last login was more than the threshold ago, require OTP verification for security

### 3. Configuration

- **`LOGIN_OTP_THRESHOLD_DAYS`**: Environment variable to configure the threshold (default: 7 days)
- Can be set in `.env` file: `LOGIN_OTP_THRESHOLD_DAYS=7`

### 4. API Changes

#### Updated Login Endpoint (`POST /api/v1/auth/login`)

The login endpoint now returns different response types based on whether OTP is required:

**When OTP is NOT required (recent login):**
```json
{
    "access_token": "...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "...",
    "user_id": "123",
    "message": "Login successful - welcome back!",
    "otp_required": false
}
```

**When OTP IS required (first login or > threshold days):**
```json
{
    "message": "For security, please verify with the OTP sent to your email",
    "login_request_id": "123",
    "expires_in": 300
}
```

### 5. Frontend Updates

- **New `DirectLoginResponse` type** for handling direct login responses
- **Updated `useLogin` hook** with additional callback options:
  - `onDirectLogin`: Called when user gets direct access (no OTP needed)
  - `onOtpRequired`: Called when OTP verification is needed
- **Automatic token storage** for direct login responses

## Benefits

1. **Better User Experience**: Frequent users don't need to verify OTP every time
2. **Maintained Security**: Inactive users still require verification
3. **Configurable**: Administrators can adjust the threshold based on security requirements
4. **Backward Compatible**: Existing OTP verification flow remains unchanged

## Security Considerations

- First-time users always require OTP verification
- Users who haven't logged in for more than the threshold period require OTP
- Google OAuth users also have their login time tracked
- The threshold is configurable to balance security and usability

## Usage Examples

### Setting Custom Threshold

```bash
# In .env file
LOGIN_OTP_THRESHOLD_DAYS=14  # Require OTP after 14 days instead of 7
```

### Frontend Implementation

```typescript
const { login } = useLogin({
    onDirectLogin: (response) => {
        // User logged in directly, tokens are already stored
        console.log("Welcome back!", response.message);
        navigate('/dashboard');
    },
    onOtpRequired: (response) => {
        // User needs to verify OTP
        console.log("Please check your email for verification code");
        setShowOtpForm(true);
        setLoginRequestId(response.login_request_id);
    }
});
```

This update significantly improves the user experience while maintaining strong security practices. 