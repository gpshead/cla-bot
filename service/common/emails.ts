/**
 * Validates a single email address value.
 */
export function validateEmail(value: string): boolean {
  return /^([a-zA-Z0-9_\-\.\+]+)@([a-zA-Z0-9_\-\.\+]+)\.([a-zA-Z]{2,5}){1,25}$/
    .test(value);
}
