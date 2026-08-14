/** Idle / absolute session policy for the member portal. */

/** Log out after this long with no user activity. */
export const SESSION_IDLE_MS = 20 * 60 * 1000

/** Show “about to timeout” warning this long before idle logout. */
export const SESSION_WARNING_BEFORE_MS = 2 * 60 * 1000

/** Force re-login even if the user stays active. */
export const SESSION_ABSOLUTE_MS = 12 * 60 * 60 * 1000

/** Ignore activity bursts closer than this. */
export const SESSION_ACTIVITY_THROTTLE_MS = 1000

export const SESSION_TIMEOUT_MESSAGE =
  'Your session timed out. Please login again.'

export const SESSION_TIMEOUT_REASON = 'timeout'
