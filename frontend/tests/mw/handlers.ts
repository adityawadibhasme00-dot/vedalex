import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('http://localhost/api/v1/health', () =>
    HttpResponse.json({
      status: 'healthy',
      version: 'test',
      database: 'connected'
    })
  ),
  http.post('http://localhost/api/v1/auth/login', () =>
    HttpResponse.json({
      access_token: 'test-token',
      token_type: 'bearer',
      user: {
        id: 'test-user',
        name: 'Test User',
        email: 'tester@example.test',
        role: 'researcher'
      }
    })
  )
];
