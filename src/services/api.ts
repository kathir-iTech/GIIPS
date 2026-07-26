import type { DashboardData } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
if (!BASE_URL) {
    throw new Error("VITE_API_BASE_URL is required but not set. Define it in your .env file.");
}

const FETCH_DEFAULTS: RequestInit = {
  credentials: 'include',
};

const TIMEOUT_MS = 30_000;

class NetworkError extends Error {
  constructor(message: string, public readonly isTimeout: boolean, public readonly original?: unknown) {
    super(message);
    this.name = 'NetworkError';
  }
}

const fetchWithTimeout = async (url: string, options: RequestInit, timeoutMs: number = TIMEOUT_MS): Promise<Response> => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new NetworkError('Connection timed out. Please check your internet and try again.', true, err);
    }
    if (err instanceof TypeError && err.message === 'Failed to fetch') {
      throw new NetworkError('Could not reach the server. Please check your internet connection and try again.', false, err);
    }
    throw new NetworkError(err.message || 'A network error occurred. Please try again.', false, err);
  } finally {
    clearTimeout(timer);
  }
};

const safeJson = async (response: Response) => {
  try {
    return await response.json();
  } catch {
    return {};
  }
};

const detailToMessage = (detail: unknown): string => {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ');
  if (typeof detail === 'object' && detail !== null) return JSON.stringify(detail);
  return '';
};

const getErrorMessage = async (response: Response): Promise<string> => {
  try {
    const body = await response.json();
    return detailToMessage(body.detail) || body.message || body.error || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
};

export const api = {
  getDashboardData: async (): Promise<DashboardData> => {
    const response = await fetch(`${BASE_URL}/dashboard`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  submitComplaint: async (payload: any): Promise<any> => {
    const response = await fetchWithTimeout(`${BASE_URL}/complaints`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await safeJson(response);
    if (!response.ok) {
      throw new Error(detailToMessage(data.detail) || `Server error (${response.status}). Please try again.`);
    }
    return data;
  },

  getComplaintStatus: async (complaintId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}/status`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  uploadComplaintPhoto: async (complaintId: string, file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetchWithTimeout(`${BASE_URL}/complaints/${complaintId}/upload`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      body: formData,
    }, 30_000);
    const data = await safeJson(response);
    if (!response.ok) {
      throw new Error(detailToMessage(data.detail) || `Photo upload failed (server error ${response.status}).`);
    }
    return data;
  },

  getHeatmap: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/heatmap`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getHotspots: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/hotspots`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getForecast: async (days: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/forecast?days=${days}`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getRiskAnalysis: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/risk`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  simulateResources: async (additional_teams: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/simulate?additional_teams=${additional_teams}`, { ...FETCH_DEFAULTS, method: 'POST' });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getIncidents: async (sortField?: string, limit?: number): Promise<any[]> => {
    let url = `${BASE_URL}/incidents`;
    const params: string[] = [];
    if (sortField) params.push(`sort=${encodeURIComponent(sortField)}`);
    if (limit) params.push(`limit=${limit}`);
    if (params.length) url += `?${params.join('&')}`;
    const response = await fetch(url, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    const data = await response.json();
    return data.incidents || [];
  },

  getClusterDetail: async (incidentId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  getClassificationMetrics: async (): Promise<any> => {
    const [metricsRes, trendRes] = await Promise.all([
      fetch(`${BASE_URL}/dashboard/metrics`, FETCH_DEFAULTS),
      fetch(`${BASE_URL}/dashboard/trend`, FETCH_DEFAULTS)
    ]);

    if (!metricsRes.ok || !trendRes.ok) {
      throw new Error('API Error: Failed to fetch metrics or trend data');
    }

    const metrics = await metricsRes.json();
    const trend = await trendRes.json();

    const accuracy = metrics.model_accuracy ?? 0;
    const precision = metrics.model_precision ?? 0;
    const recall = metrics.model_recall ?? 0;

    const f1Score =
      precision + recall > 0
        ? (2 * precision * recall) / (precision + recall)
        : 0;

    return {
      accuracy: accuracy / 100,
      precision: precision / 100,
      recall: recall / 100,
      f1Score: f1Score / 100,
      datasetSize: metrics.dataset_size ?? 0,
      modelType: metrics.model_type || '',
      categories: metrics.categories || [],
      categoryDistribution: Array.isArray(metrics.category_distribution) ? metrics.category_distribution : [],
      confusionMatrix: Array.isArray(metrics.confusion_matrix) ? metrics.confusion_matrix : [],
      trendData: (trend.labels || []).map((label: string, i: number) => ({
        month: label,
        complaints: (trend.complaints || [])[i] ?? 0,
        incidents: (trend.incidents || [])[i] ?? 0
      }))
    };
  },
  
  getExecutiveSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/executive/summary`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getWardHealth: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/executive/ward-health`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getDeptWorkload: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/executive/department-workload`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  login: async (email: string, password: string): Promise<any> => {
    const response = await fetchWithTimeout(`${BASE_URL}/auth/login`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(detailToMessage(error.detail) || 'Login failed. Please check your credentials and try again.');
    }
    return response.json();
  },

  register: async (data: {
    full_name: string;
    email: string;
    password: string;
    phone?: string;
    district?: string;
    ward?: string;
  }): Promise<any> => {
    const response = await fetchWithTimeout(`${BASE_URL}/auth/register`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(detailToMessage(error.detail) || 'Registration failed. Please try again.');
    }
    return response.json();
  },

  logout: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/auth/logout`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
    });
    return response.json();
  },

  getMe: async (): Promise<any> => {
    const response = await fetchWithTimeout(`${BASE_URL}/auth/me`, {
      ...FETCH_DEFAULTS,
      method: 'GET',
    }, 30_000);
    if (!response.ok) {
      throw new Error('Not authenticated');
    }
    return response.json();
  },

  updateProfile: async (data: any): Promise<any> => {
    const response = await fetch(`${BASE_URL}/auth/profile`, {
      ...FETCH_DEFAULTS,
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(detailToMessage(error.detail) || 'Failed to update profile');
    }
    return response.json();
  },

  getComplaintCoordinates: async (): Promise<any[]> => {
    const response = await fetch(`${BASE_URL}/complaints/coordinates`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getMyComplaints: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/my`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  getComplaintDetail: async (complaintId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  getComplaintPhoto: async (complaintId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}/photo`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  get: async (endpoint: string): Promise<Response> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, FETCH_DEFAULTS);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response;
  },

  post: async (endpoint: string, data: any): Promise<Response> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response;
  },

  patch: async (endpoint: string, data: any): Promise<Response> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...FETCH_DEFAULTS,
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response;
  },

  getAnalytics: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/dashboard/analytics`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getSystemHealth: async (): Promise<any> => {
    const response = await api.get('/admin/system-health');
    return response.json();
  },

  getPredictionsSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/predictions/summary`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getPriorityRules: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/priority/rules`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getKnowledgeSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/knowledge/summary`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getDecisionSupportSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/decision-support/summary`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  mergeIncidents: async (incidentIds: string[]): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/merge`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_ids: incidentIds })
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  splitComplaint: async (incidentId: string, complaintId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/split/${complaintId}`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  copilotChat: async (message: string, history: any[] = []): Promise<any> => {
    const response = await fetch(`${BASE_URL}/copilot/chat`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history })
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getNotifications: async (): Promise<any[]> => {
    const response = await fetch(`${BASE_URL}/notifications`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  markNotificationRead: async (id: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/notifications/${id}/read`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  markAllNotificationsRead: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/notifications/read-all`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getWardComplaints: async (ward: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/ward/${encodeURIComponent(ward)}`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  escalateIncident: async (incidentId: string, reason: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/escalate`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getEscalatedIncidents: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/escalated`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  autoEscalateIncidents: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/auto-escalate`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  postIncidentUpdate: async (incidentId: string, message: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/updates`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  bulkUpdateIncidents: async (payload: { incident_ids: string[], action: string, message?: string }): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/bulk-update`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  updateIncidentStatus: async (incidentId: string, status: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/status`, {
      ...FETCH_DEFAULTS,
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  verifyResolution: async (incidentId: string, code: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/verify-resolution`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  rateComplaint: async (complaintId: string, rating: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}/rate`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  updateComplaint: async (complaintId: string, data: { description?: string; location?: string }): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}`, {
      ...FETCH_DEFAULTS,
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  trackComplaint: async (complaintId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/track/${encodeURIComponent(complaintId)}`);
    if (!response.ok) {
      const err = await safeJson(response);
      throw new Error(detailToMessage(err.detail) || `Complaint not found (${response.status})`);
    }
    return response.json();
  },

  getPublicStats: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/public/stats`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getSuccessStories: async (ward?: string): Promise<any> => {
    const params = ward ? `?ward=${encodeURIComponent(ward)}` : '';
    const response = await fetch(`${BASE_URL}/public/success-stories${params}`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getWardStats: async (ward: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/public/ward-stats/${encodeURIComponent(ward)}`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  updateNotificationPrefs: async (notify_status_updates: boolean): Promise<any> => {
    const response = await fetch(`${BASE_URL}/auth/profile/notifications`, {
      ...FETCH_DEFAULTS,
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notify_status_updates }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  reopenIncident: async (incidentId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/reopen`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  appealIncident: async (incidentId: string, reason: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}/appeal`, {
      ...FETCH_DEFAULTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getWsToken: async (): Promise<string> => {
    const response = await fetch(`${BASE_URL}/auth/ws-token`, FETCH_DEFAULTS);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    const data = await response.json();
    return data.token;
  },

  getWsUrl: (token: string): string => {
    const wsBase = BASE_URL.replace(/^http/, 'ws');
    return `${wsBase}/ws/dashboard?token=${encodeURIComponent(token)}`;
  },
};