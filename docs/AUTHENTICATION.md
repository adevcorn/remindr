# Authentication Flow

## Overview

Remindr uses a **two-phase authentication flow** that separates user authentication from Google API access:

1. **Phase 1: Sign In with Google (ID Token Flow)** - Fast authentication using Google Sign-In SDK
2. **Phase 2: Connect Google Services (OAuth Token Flow)** - Optional connection for Google Tasks/Calendar sync

This approach provides better UX (immediate sign-in) while maintaining full OAuth capabilities for sync features.

## Architecture

### Two-Phase Flow Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Mobile    │         │   Backend    │         │   Google    │
│     App     │         │    Server    │         │   OAuth     │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ ═══════════════════════════════════════════════│════════════
       │ PHASE 1: SIGN IN (ID Token Authentication)    │
       │ ═══════════════════════════════════════════════│════════════
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
       │                       │    (No OAuth tokens)   │
       │                       │                        │
       │ 9. Session Token      │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │ 10. User is signed in │                        │
       │     (can use app)     │                        │
       │                       │                        │
       │ ═══════════════════════════════════════════════│════════════
       │ PHASE 2: CONNECT GOOGLE SERVICES (OAuth)      │
       │ ═══════════════════════════════════════════════│════════════
       │                       │                        │
       │ 11. User taps         │                        │
       │     "Connect Google"  │                        │
       │                       │                        │
       │ 12. GET /auth/connect-google                  │
       │     Authorization:    │                        │
       │     Bearer <session>  │                        │
       ├──────────────────────>│                        │
       │                       │                        │
       │ 13. OAuth URL + State │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │ 14. Open OAuth URL    │                        │
       │     in browser        │                        │
       ├──────────────────────────────────────────────>│
       │                       │                        │
       │                       │    15. User grants     │
       │                       │        Calendar/Tasks  │
       │                       │        permissions     │
       │                       │                        │
       │ 16. Redirect with code│                        │
       │<──────────────────────────────────────────────┤
       │                       │                        │
       │ 17. GET /auth/callback?code=...&state=...     │
       │                       │                        │
       │                       │ 18. Exchange code      │
       │                       │     for tokens         │
       │                       ├───────────────────────>│
       │                       │                        │
       │                       │ 19. Access + Refresh   │
       │                       │     tokens             │
       │                       │<───────────────────────┤
       │                       │                        │
       │                       │ 20. Store tokens       │
       │                       │     in User record     │
       │                       │                        │
       │ 21. Success response  │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │ 22. Google sync       │                        │
       │     now enabled       │                        │
       │                       │                        │
```

## Why Two Phases?

### Problem with Single-Phase OAuth
- ID token verification is fast and simple (one API call)
- Full OAuth flow requires browser redirects and is slower
- Users want immediate app access, not permission dialogs

### Solution: Separate Concerns
1. **Phase 1 (ID Token)**: Proves user identity, creates session, user is signed in
2. **Phase 2 (OAuth)**: Optional, only for users who want Google sync

### Benefits
- ✅ **Faster sign-in**: No OAuth redirect for basic auth
- ✅ **Better UX**: Users can use app immediately, connect sync later
- ✅ **Clear permissions**: Users understand they're granting Calendar/Tasks access
- ✅ **Flexible**: Can add more integrations (Outlook, etc.) without changing auth
- ✅ **Testable**: Can test app without Google API credentials

## Implementation Details

### Phase 1: Sign In with Google (ID Token)

**Mobile App**: `mobile/lib/services/auth_service.dart`

1. **Google Sign-In**: Uses Google Sign-In SDK to authenticate user client-side
2. **ID Token Extraction**: Extracts ID token from authentication result
3. **Backend Verification**: Sends ID token to backend `/auth/google-token` endpoint
4. **Session Storage**: Stores returned session token in secure storage
5. **API Authentication**: Uses session token for all API calls

**Key Methods**:
- `signInWithGoogle()`: Complete sign-in flow
- `initialize()`: Restore session on app start
- `signOut()`: Clear session
- `handleUnauthorized()`: Handle 401 errors

**Backend**: `backend/app/api/endpoints/auth.py`

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
1. Verify ID token with Google's servers
2. Extract user info (user_id, email, name)
3. Create or update User record (without OAuth tokens)
4. Create Session record with 30-day expiry
5. Return session token

**Note**: OAuth tokens (google_access_token, google_refresh_token) are NOT populated in this phase.

### Phase 2: Connect Google Services (OAuth)

**Mobile App**: `mobile/lib/services/oauth_service.dart`

**Flow**:
1. User taps "Connect Google Services" button
2. App calls `/auth/connect-google` to get OAuth URL
3. App opens OAuth URL in browser/webview
4. User grants Calendar & Tasks permissions
5. Google redirects to `/auth/callback` with code
6. Backend exchanges code for tokens and stores them
7. App checks connection status
8. Google sync is enabled

**Backend Endpoints**:

#### `GET /auth/connect-google`
Initiate OAuth flow for authenticated user (requires session token).

**Headers**:
```
Authorization: Bearer <session_token>
```

**Response** (200 OK):
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "random_state_token"
}
```

**Process**:
1. Verify user is authenticated (session token required)
2. Generate OAuth authorization URL with state parameter
3. Store state with user_id for validation in callback
4. Return OAuth URL to mobile app

#### `GET /auth/callback?code=...&state=...`
OAuth callback handler (handles both login and connect flows).

**Query Parameters**:
- `code`: Authorization code from Google
- `state`: State parameter for CSRF protection

**Response for Connect Flow** (200 OK):
```json
{
  "success": true,
  "message": "Google services connected successfully",
  "email": "user@example.com"
}
```

**Process**:
1. Validate state parameter
2. Exchange authorization code for access/refresh tokens
3. Get user info from Google
4. If state has user_id (connect flow):
   - Verify email matches authenticated user
   - Update user's OAuth tokens
   - Return success message
5. If state has no user_id (legacy login flow):
   - Create/update user with tokens
   - Create session
   - Return session token

#### `GET /auth/google-connection-status`
Check if user has connected Google services (requires session token).

**Headers**:
```
Authorization: Bearer <session_token>
```

**Response** (200 OK):
```json
{
  "connected": true,
  "email": "user@example.com",
  "has_tasks_scope": true,
  "has_calendar_scope": true
}
```

**Process**:
1. Look up user from session token
2. Check if google_access_token and google_refresh_token exist
3. Parse google_scopes to check which services are connected
4. Return connection status

### User Experience Flow

1. **First Launch**:
   - User opens app
   - Sees "Sign In with Google" button
   - Taps button → Google Sign-In SDK → Signed in (Phase 1)
   - Sees home screen with orange banner: "Connect Google Calendar & Tasks to sync"

2. **Connect Google Services**:
   - User taps "Connect Google Services" button
   - Browser/webview opens with Google OAuth consent screen
   - User grants Calendar & Tasks permissions
   - Redirects back to app
   - Banner changes to green: "Google Calendar & Tasks connected"
   - Captures now sync to Google

3. **Subsequent Launches**:
   - User opens app
   - Session restored automatically
   - If connected, green banner shows
   - If not connected, orange banner shows (can connect anytime)

### Mobile UI Components

**Home Screen Banner** (`mobile/lib/screens/home_screen.dart`):

```dart
// Before connection - orange banner
Card(
  color: Colors.orange.shade50,
  child: Column(
    children: [
      Text('Connect Google Calendar & Tasks to sync your captures'),
      ElevatedButton(
        onPressed: _connectGoogleServices,
        child: Text('Connect Google Services'),
      ),
    ],
  ),
)

// After connection - green banner
Card(
  color: Colors.green.shade50,
  child: Row(
    children: [
      Icon(Icons.check_circle, color: Colors.green),
      Text('Google Calendar & Tasks connected'),
    ],
  ),
)
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
