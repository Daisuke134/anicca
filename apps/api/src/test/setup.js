import { vi, beforeEach } from 'vitest';
import { mockDeep, mockReset } from 'vitest-mock-extended';

const prismaMock = mockDeep();

vi.mock('../lib/prisma.js', () => ({
  prisma: prismaMock
}));

// Logger mock — prevent actual logging and config dependencies
const loggerMock = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  debug: vi.fn(),
  withContext: vi.fn(() => loggerMock),
};

vi.mock('../utils/logger.js', () => ({
  default: loggerMock,
}));

vi.mock('../lib/logger.js', () => ({
  logger: loggerMock,
}));

beforeEach(() => {
  mockReset(prismaMock);
  vi.clearAllMocks();
});

export { prismaMock, loggerMock };
