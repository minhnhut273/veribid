import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { fetchAuthSession } = vi.hoisted(() => ({ fetchAuthSession: vi.fn() }));
vi.mock('aws-amplify/auth', () => ({ fetchAuthSession }));

import { api } from './api';

function session(payload: Record<string, unknown>, value: string) {
  return {
    tokens: {
      accessToken: {
        payload,
        toString: () => value,
      },
    },
  };
}

describe('authenticated API requests', () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  it('refreshes a stale access token before a write when workspace or write-role claims are missing', async () => {
    fetchAuthSession
      .mockResolvedValueOnce(session({ sub: 'user-1' }, 'stale-token'))
      .mockResolvedValueOnce(session({
        sub: 'user-1',
        workspace_id: 'WS_user_1',
        'cognito:groups': ['TenantAdmin'],
      }, 'refreshed-token'));
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => ({
      ok: true,
      status: 201,
      json: async () => ({ data: { evaluation_id: 'EVAL_1', name: 'Procurement', status: 'CREATED', created_at: 'now' } }),
    } as Response));
    vi.stubGlobal('fetch', fetchMock);

    await api.createEvaluation('Procurement');

    expect(fetchAuthSession).toHaveBeenNthCalledWith(1);
    expect(fetchAuthSession).toHaveBeenNthCalledWith(2, { forceRefresh: true });
    expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).authorization).toBe('Bearer refreshed-token');
  });

  it('keeps read-only sessions from refreshing just because they lack a write role', async () => {
    fetchAuthSession.mockResolvedValueOnce(session({
      sub: 'auditor-1',
      workspace_id: 'WS_auditor_1',
      'cognito:groups': ['Auditor'],
    }, 'auditor-token'));
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => ({
      ok: true,
      status: 200,
      json: async () => ({ data: { evaluation_id: 'EVAL_1', name: 'Procurement', status: 'CREATED', created_at: 'now' } }),
    } as Response));
    vi.stubGlobal('fetch', fetchMock);

    await api.getEvaluation('EVAL_1');

    expect(fetchAuthSession).toHaveBeenCalledTimes(1);
    expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).authorization).toBe('Bearer auditor-token');
  });
});
