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
  ),
  http.get('http://localhost/api/v1/auth/profile', () =>
    HttpResponse.json({
      id: 'test-user',
      name: 'Test User',
      email: 'tester@example.test',
      role: 'researcher',
      institution: null,
      is_active: true,
      created_at: '2024-01-01 00:00:00'
    })
  )
];
