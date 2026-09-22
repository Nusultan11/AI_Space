const ACCESS_TOKEN_KEY = "aispace.access-token";
export const UNAUTHORIZED_EVENT = "aispace:unauthorized";

export function getAccessToken(): string | null {
  return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function notifyUnauthorized(): void {
  clearAccessToken();
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}
