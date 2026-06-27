/**
 * Client-side file validation for the AI Swim Coach upload flow.
 *
 * Validates: Requirements 1.1, 1.2, 1.3
 */

const MAX_FILE_SIZE = 104_857_600; // 100 MB in bytes

export type ValidationResult =
  | { valid: true }
  | { valid: false; reason: string };

/**
 * Validates a File before upload.
 *
 * - Rejects files whose name does not end with `.fit` (case-insensitive).
 * - Rejects files whose size exceeds 100 MB (104,857,600 bytes).
 * - Returns `{ valid: true }` otherwise.
 */
export function validateFile(file: File): ValidationResult {
  if (!file.name.toLowerCase().endsWith('.fit')) {
    return { valid: false, reason: 'Only .fit files are accepted.' };
  }

  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, reason: 'File exceeds the 100 MB limit.' };
  }

  return { valid: true };
}
