import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { register, login, verifyToken } from './authService';
import { ApiError } from '../types';

describe('authService', () => {
  const originalFetch = globalThis.fetch;
  const mockEndpoint = 'https://api.test.com';

  beforeEach(() => {
    vi.stubEnv('VITE_API_ENDPOINT', mockEndpoint);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  describe('register', () => {
    it('should successfully register a user', async () => {
      const mockResponse = {
        user_id: '123e4567-e89b-12d3-a456-426614174000',
        email: 'test@example.com',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await register('test@example.com', 'password123');

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/auth/register`,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'test@example.com', password: 'password123' }),
        }),
      );
    });

    it('should throw ApiError on 409 conflict', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        text: async () => 'Email already exists',
      });

      await expect(register('test@example.com', 'password123')).rejects.toThrow(ApiError);
      const error = await register('test@example.com', 'password123').catch((e) => e);
      expect(error.status).toBe(409);
      expect(error.serverMessage).toBe('An account with this email already exists.');
    });

    it('should throw ApiError on network failure', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(register('test@example.com', 'password123')).rejects.toThrow(ApiError);
      await expect(register('test@example.com', 'password123')).rejects.toThrow(
        'Could not reach the server',
      );
    });
  });

  describe('login', () => {
    it('should successfully login and return token', async () => {
      const mockResponse = {
        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        user_id: '123e4567-e89b-12d3-a456-426614174000',
        email: 'test@example.com',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await login('test@example.com', 'password123');

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/auth/login`,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'test@example.com', password: 'password123' }),
        }),
      );
    });

    it('should throw ApiError on 401 unauthorized', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => 'Invalid credentials',
      });

      await expect(login('test@example.com', 'wrongpassword')).rejects.toThrow(ApiError);
      const error = await login('test@example.com', 'wrongpassword').catch((e) => e);
      expect(error.status).toBe(401);
      expect(error.serverMessage).toBe('Invalid email or password.');
    });
  });

  describe('verifyToken', () => {
    it('should successfully verify token', async () => {
      const mockResponse = {
        user_id: '123e4567-e89b-12d3-a456-426614174000',
        email: 'test@example.com',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await verifyToken('valid-jwt-token');

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/auth/verify`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            Authorization: 'Bearer valid-jwt-token',
          },
        }),
      );
    });

    it('should throw ApiError on invalid token', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => 'Token expired',
      });

      await expect(verifyToken('invalid-token')).rejects.toThrow(ApiError);
    });
  });
});
