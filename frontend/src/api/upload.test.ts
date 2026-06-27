import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { uploadFitFile } from './upload';
import { ApiError } from '../types';

describe('uploadFitFile', () => {
  const mockFile = new File(['binary-content'], 'workout.fit', {
    type: 'application/octet-stream',
  });

  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.stubEnv('VITE_API_ENDPOINT', 'https://api.example.com');
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  it('sends a POST with FormData containing the file', async () => {
    const mockResponse = {
      ok: true,
      json: () => Promise.resolve({ tips: ['a', 'b', 'c'], drill: 'd' }),
    };
    globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

    await uploadFitFile(mockFile);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'https://api.example.com/upload',
      expect.objectContaining({ method: 'POST' }),
    );

    const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = callArgs[1].body as FormData;
    expect(body.get('file')).toBe(mockFile);
  });

  it('returns CoachingResponse on success', async () => {
    const coaching = { tips: ['tip1', 'tip2', 'tip3'], drill: 'drill1' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(coaching),
    });

    const result = await uploadFitFile(mockFile);
    expect(result).toEqual(coaching);
  });

  it('throws ApiError with mapped message for 400', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      text: () => Promise.resolve('Bad request'),
    });

    await expect(uploadFitFile(mockFile)).rejects.toThrow(ApiError);
    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 400,
      serverMessage: 'The file could not be read — please try a different .fit file.',
    });
  });

  it('throws ApiError with mapped message for 413', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 413,
      text: () => Promise.resolve('Payload too large'),
    });

    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 413,
      serverMessage: 'The file is too large for this endpoint (max 10 MB).',
    });
  });

  it('throws ApiError with server body text for 422', async () => {
    const serverMsg = 'Missing metrics: pace, SWOLF';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: () => Promise.resolve(serverMsg),
    });

    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 422,
      serverMessage: serverMsg,
    });
  });

  it('throws ApiError with mapped message for 502', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      text: () => Promise.resolve('Bad gateway'),
    });

    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 502,
      serverMessage: 'Our AI coach is temporarily unavailable. Please try again.',
    });
  });

  it('throws ApiError with generic 5xx message for 500', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal server error'),
    });

    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 500,
      serverMessage: 'A server error occurred. Please try again in a moment.',
    });
  });

  it('throws ApiError with generic 5xx message for 503', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      text: () => Promise.resolve('Service unavailable'),
    });

    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 503,
      serverMessage: 'A server error occurred. Please try again in a moment.',
    });
  });

  it('throws ApiError with network error message when fetch rejects', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(uploadFitFile(mockFile)).rejects.toMatchObject({
      status: 0,
      serverMessage: 'Could not reach the server. Check your connection and retry.',
    });
  });
});
