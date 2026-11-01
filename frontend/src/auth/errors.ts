/** Turn Cognito/Amplify errors into messages that tell the user what to do next. */
const MESSAGES: Record<string, string> = {
  NotAuthorizedException: "That email and password don't match. Check both and try again.",
  UserNotFoundException: "That email and password don't match. Check both and try again.",
  UsernameExistsException: "An account with this email already exists. Sign in instead.",
  InvalidPasswordException: "That password doesn't meet the requirements listed below the field.",
  CodeMismatchException: "That code isn't right. Check the latest email and try again.",
  ExpiredCodeException: "That code has expired. Send a new one and use the latest email.",
  LimitExceededException: "Too many attempts. Wait a few minutes, then try again.",
  TooManyRequestsException: "Too many attempts. Wait a few minutes, then try again.",
  InvalidParameterException: "Some details aren't valid. Check the email address and try again.",
  NetworkError: "Can't reach the sign-in service. Check your connection and try again.",
};

export function authErrorMessage(error: unknown): string {
  const name = error instanceof Error ? error.name : "";
  return MESSAGES[name] ?? "Something went wrong with sign-in. Try again in a moment.";
}
