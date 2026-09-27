import { TransformStream } from 'stream/web';
import { TextDecoder, TextEncoder } from 'util';
import { BroadcastChannel } from 'worker_threads';
import '@testing-library/jest-dom';
import 'whatwg-fetch';

Object.assign(globalThis, { BroadcastChannel, TextDecoder, TextEncoder, TransformStream });

const { server } = require('./tests/mw/server') as typeof import('./tests/mw/server');

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => server.close());
