export const AUTH_COOKIE_NAME = "access_token";

export function isAuthenticated(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split(";").some((part) => part.trim().startsWith(`${AUTH_COOKIE_NAME}=`));
}
