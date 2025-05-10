# Authentication API

## Overview

BiteWise offers multiple authentication methods to ensure a secure and convenient user experience:

1. **Email/Password Authentication** with email OTP verification
2. **Google Social Login** integration
3. **Token-based API Authentication** for all protected endpoints

All new account registrations, regardless of method, will receive an "Activate Your Account" email to verify their identity.

Resend for email service and fastapi-sso for google login

## Base URL

```
https://{hosted_url}/v1/auth
```

## Authentication Endpoints

### Email & Password Registration

```http
POST /register
```

Registers a new user account with email and password. An OTP verification email will be sent to the provided email address.

**Request Body**:

```json
{
  "email": "string",
  "password": "string",
  "username": "string",
  "full_name": "string"
}
```

**Response** (201 Created):

```json
{
  "user_id": "string",
  "email": "string",
  "message": "Verification email sent. Please check your inbox to verify your account."
}
```

### Email Verification with OTP

```http
POST /verify-email
```

Verifies the user's email address using the OTP sent to their email.

**Request Body**:

```json
{
  "email": "string",
  "otp": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Email verified successfully",
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Email & Password Login

```http
POST /login
```

Authenticates a user with email and password. An OTP will be sent to the user's email for two-factor authentication.

**Request Body**:

```json
{
  "email": "string",
  "password": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "OTP sent to your email for verification",
  "login_request_id": "string",
  "expires_in": 300
}
```

### Login OTP Verification

```http
POST /verify-login
```

Verifies the login OTP and returns an access token upon successful verification.

**Request Body**:

```json
{
  "login_request_id": "string",
  "otp": "string"
}
```

**Response** (200 OK):

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "string",
  "user_id": "string"
}
```

### Google Login

```http
GET /google/login
```

Initiates the Google OAuth2 login flow by redirecting to Google's authentication page.

**Response**: Redirects to Google's authentication page.

### Google Callback

```http
GET /google/callback
```

Handles the callback from Google OAuth2 after successful authentication.

**Query Parameters**:

- `code` (string, required): The authorization code from Google
- `state` (string, required): Anti-forgery state token

**Response** (200 OK):

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "string",
  "user_id": "string",
  "is_new_user": boolean
}
```

If `is_new_user` is `true`, an "Activate Your Account" email will be sent to the user's email address.

### Refresh Token

```http
POST /refresh
```

Obtains a new access token using a refresh token.

**Request Body**:

```json
{
  "refresh_token": "string"
}
```

**Response** (200 OK):

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Logout

```http
POST /logout
```

Invalidates the current access token and associated refresh tokens.

**Headers**:

- `Authorization` (string, required): Bearer token

**Response** (200 OK):

```json
{
  "message": "Successfully logged out"
}
```

### Password Reset Request

```http
POST /reset-password/request
```

Initiates a password reset by sending a reset link to the user's email.

**Request Body**:

```json
{
  "email": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Password reset instructions sent to your email",
  "reset_request_id": "string",
  "expires_in": 900
}
```

### Password Reset Completion

```http
POST /reset-password/complete
```

Completes the password reset process with the OTP and new password.

**Request Body**:

```json
{
  "reset_request_id": "string",
  "otp": "string",
  "new_password": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Password reset successful"
}
```

## Error Handling

All authentication endpoints follow a consistent error response format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### Common Error Codes

- `400` - Bad Request: Malformed request or invalid parameters
- `401` - Unauthorized: Authentication failure
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource not found
- `409` - Conflict: Email already registered
- `422` - Unprocessable Entity: Valid request but unable to process
- `429` - Too Many Requests: Rate limit exceeded (e.g., too many OTP attempts)
- `500` - Internal Server Error: Server-side error

## Implementation Notes

### Email Service Configuration

BiteWise uses Resend as the email service provider for sending verification emails, OTPs, and account notifications. Key email templates include:

1. **Account Verification**: Sent after registration with OTP
2. **Login Verification**: Sent during login with OTP
3. **Password Reset**: Sent when a password reset is requested
4. **Account Activation**: Sent to users who register via Google login

### Google OAuth Integration

BiteWise implements Google OAuth using the FastAPI-SSO library, which simplifies the OAuth flow:

1. User is redirected to Google login page
2. After successful authentication, Google redirects back to the callback URL
3. The callback handler processes the authentication data and creates or retrieves the user account
4. An authentication token is issued to the user

### Security Considerations

- OTPs expire after 5 minutes for added security
- Access tokens are valid for 1 hour
- Refresh tokens are valid for 30 days
- Failed login attempts are rate-limited to prevent brute force attacks
- All sensitive data is encrypted in transit and at rest