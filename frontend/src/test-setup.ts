// Vitest / React Testing Library global setup
import '@testing-library/jest-dom'

// Mock ResizeObserver for recharts (not available in jsdom)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
