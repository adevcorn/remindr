# Authentication Flow

## Overview

Remindr uses a mobile-friendly OAuth flow with Google Sign-In. This approach is simpler and more reliable for mobile applications than traditional web-based OAuth redirects.

## Architecture

### Flow Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Mobile    │         │   Backend    │         │   Google    │
│     App     │         │    Server    │         │   OAuth     │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ 1. User taps         │                        │
       │    "Sign In"         │                        │
       │                       │                        │
       │ 2. Google Sign-In SDK │                       │
       ├──────────────────────────────────────────────>│
       │                       │                        │
       │                       │    3. User consents   │
       │                       │                        │
       │ 4. ID Token           │                        │
       │<──────────────────────────────────────────────┤
       │                       │                        │
       │ 5. POST /auth/google-token                    │
       │      {id_token}       │                        │
       ├──────────────────────>│                        │
       │                       │                        │
       │                       │ 6. Verify ID Token     │
       │                       ├───────────────────────>│
       │                       │                        │
       │                       │ 7. Token Valid         │
       │                       │<───────────────────────┤
       │                       │                        │
       │                       │ 8. Create Session      │
       │                       │    in Database         │
       │                       │                        │
       │ 9. Session Token      │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │ 10. Store in          │                        │
       │     Secure Storage    │                        │
       │                       │                        │
```

## Implementation Details

### Mobile App (Flutter)

**Location**: `mobile/lib/services/auth_service.dart`

1. **Google Sign-In**: Uses Google Sign-In SDK to authenticate user client-side
2. **ID Token Extraction**: Extracts ID token from authentication result
3. **Backend Verification**: Sends ID token to backend `/auth/google-token` endpoint
4. **Session Storage**: Stores returned session token in secure storage (FlutterSecureStorage)
5. **API Authentication**: Uses session token in Authorization header for all API calls

**Key Methods**:
- `signInWithGoogle()`: Complete sign-in flow
- `initialize()`: Restore session on app start, verify token validity
- `signOut()`: Clear session locally and on backend
- `handleUnauthorized()`: Clear session on 401 errors
- `checkSessionValid()`: Check if session is still valid

### Backend (FastAPI)

**Location**: `backend/app/api/endpoints/auth.py`

**Endpoints**:

#### `POST /auth/google-token`
Accepts Google ID token and returns session token.

**Request**:
```json
{
  "id_token": "eyJhbGc..."
}
```

**Response** (200 OK):
```json
{
  "session_token": "abc123...",
  "user_id": "google_user_123",
  "email": "user@example.com",
  "name": "User Name"
}
```

**Process**:
1. Verify ID token with Google's servers using `google.oauth2.id_token.verify_oauth2_token()`
2. Extract user info (user_id, email, name) from verified token
3. Create or update User record in database
4. Create Session record with 30-day expiry
5. Return session token to mobile app

#### `GET /auth/me`
Get current user info (requires authentication).

**Headers**:
```
Authorization: Bearer <session_token>
```

**Response** (200 OK):
```json
{
  "user_id": "google_user_123",
  "email": "user@example.com",
  "name": "User Name",
  "created_at": "2025-11-01T12:00:00Z",
  "last_login_at": "2025-11-08T10:30:00Z"
}
```

#### `POST /auth/logout`
Revoke current session (requires authentication).

**Headers**:
```
Authorization: Bearer <session_token>
```

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

### Session Management

**Location**: `backend/app/core/auth.py`

**Session Properties**:
- **Expiry**: 30 days from creation (configurable via `expires_hours` parameter)
- **Storage**: Database table `sessions` with columns:
  - `session_token`: Secure random token (32 bytes, URL-safe)
  - `user_id`: Foreign key to users table
  - `expires_at`: Expiration timestamp
  - `last_accessed_at`: Last API call timestamp
  
**Validation** (`get_current_user_id`):
1. Extract token from Authorization header
2. Look up session in database
3. Check if expired (auto-delete if expired)
4. Update `last_accessed_at` timestamp
5. Return user_id for authorized endpoints

**Security**:
- Session tokens are cryptographically secure (32 bytes from `secrets.token_urlsafe()`)
- Expired sessions are automatically deleted on access
- All protected endpoints use `Depends(get_current_user_id)` for authentication

## Token Expiry Behavior

**Session Expiry**: 30 days from last login

**When Session Expires**:
1. Backend returns 401 Unauthorized on any API call
2. Mobile app detects 401 and calls `handleUnauthorized()`
3. Local session is cleared
4. User is prompted to sign in again

**User Experience**:
- Acceptable for MVP (no refresh token implementation needed)
- Clear message to user: "Your session has expired. Please sign in again."
- Sign-in process is quick (one tap with Google)

## Security Considerations

### ✅ Implemented
- ID tokens verified with Google's servers (prevents token forgery)
- Session tokens stored in secure storage (not plain text)
- Session tokens are cryptographically secure random strings
- Automatic session cleanup on expiry
- 401 handling clears compromised sessions
- CSRF protection not needed (token-based auth, no cookies)

### 🔄 Future Enhancements (Post-MVP)
- Refresh token support for longer sessions without re-login
- Device fingerprinting for suspicious activity detection
- Rate limiting on authentication endpoints (already implemented via SlowAPI)
- Session revocation on password/security changes
- Multi-device session management

## Testing

### Backend Tests
**Location**: `backend/tests/test_auth_integration.py`

**Test Coverage**:
- ✅ Valid ID token authentication (new user)
- ✅ Valid ID token authentication (existing user)
- ✅ Invalid ID token rejection
- ✅ Invalid issuer rejection
- ✅ Missing email rejection
- ✅ Session token storage and retrieval
- ✅ `/me` endpoint with valid token
- ✅ `/me` endpoint with expired token (401)
- ✅ `/logout` endpoint revokes session
- ✅ 401 on missing token
- ✅ Session expiry after 30 days
- ✅ `last_accessed_at` updates on requests

### Mobile Tests
**Location**: `mobile/test/services/auth_service_test.dart`

**Test Coverage**:
- ✅ Successful sign-in with ID token
- ✅ User cancellation
- ✅ Missing ID token handling
- ✅ Backend error handling
- ✅ Session restoration on app start
- ✅ Invalid session cleanup
- ✅ Sign-out flow
- ✅ Token expiry detection
- ✅ 401 handling

## Migration from Old Flow

### Previous Implementation (Removed)
- Web-based OAuth redirect flow (`/login` → `/callback`)
- State parameter for CSRF protection
- Server auth code exchange pattern

### New Implementation
- Client-side Google Sign-In with ID token
- Backend ID token verification
- Direct session token return
- Simpler, more mobile-friendly

### Breaking Changes
- ❌ `/auth/login` endpoint removed (no longer needed)
- ❌ `/auth/callback` endpoint kept for compatibility but not used by mobile
- ✅ New `/auth/google-token` endpoint for mobile authentication

## Configuration

### Backend Environment Variables
```bash
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<not-needed-for-id-token-flow>
```

### Mobile Configuration
Update `mobile/lib/services/auth_service.dart`:
```dart
final GoogleSignIn _googleSignIn = GoogleSignIn(
  scopes: [
    'email',
    'profile',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar',
  ],
);
```

## Troubleshooting

### "Invalid ID token" Error
- **Cause**: Token expired or malformed
- **Solution**: Ensure mobile app sends fresh token, check Google Client ID matches

### "Session expired" (401)
- **Cause**: Session token older than 30 days
- **Solution**: User must sign in again (expected behavior)

### "No ID token received"
- **Cause**: Google Sign-In SDK not configured correctly
- **Solution**: Check Google Sign-In setup, OAuth consent screen, and API credentials

### Backend verification fails
- **Cause**: `GOOGLE_CLIENT_ID` mismatch
- **Solution**: Ensure backend `GOOGLE_CLIENT_ID` matches mobile app configuration

## References

- [Google Sign-In for Flutter](https://pub.dev/packages/google_sign_in)
- [Google ID Token Verification](https://developers.google.com/identity/sign-in/web/backend-auth)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Flutter Secure Storage](https://pub.dev/packages/flutter_secure_storage)
