import type { DashboardData } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
if (!BASE_URL) {
    throw new Error("VITE_API_BASE_URL is required but not set. Define it in your .env file.");
}

const safeJson = async (response: Response) => {
  try {
    return await response.json();
  } catch {
    return {};
  }
};

const getErrorMessage = async (response: Response): Promise<string> => {
  try {
    const body = await response.json();
    return body.detail || body.message || body.error || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
};

export const api = {
  getDashboardData: async (): Promise<DashboardData> => {
    const response = await fetch(`${BASE_URL}/dashboard`);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  submitComplaint: async (payload: any, token: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload),
    });
    const data = await safeJson(response);
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}` || 'Submission failed');
    }
    return data;
  },

  getComplaintStatus: async (complaintId: string, token: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}/status`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  uploadComplaintPhoto: async (complaintId: string, file: File, token: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData,
    });
    const data = await safeJson(response);
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}` || 'Upload failed');
    }
    return data;
  },

  getHeatmap: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/heatmap`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getHotspots: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/hotspots`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getForecast: async (days: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/forecast?days=${days}`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getRiskAnalysis: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/risk`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  simulateResources: async (additional_teams: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/spatial/simulate?additional_teams=${additional_teams}`, { method: 'POST' });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getIncidents: async (sortField?: string): Promise<any[]> => {
    const url = sortField
      ? `${BASE_URL}/incidents?sort=${encodeURIComponent(sortField)}`
      : `${BASE_URL}/incidents`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    const data = await response.json();
    return data.incidents || [];
  },

  getClusterDetail: async (incidentId: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/incidents/${incidentId}`);
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  getClassificationMetrics: async (): Promise<any> => {
    const [metricsRes, trendRes] = await Promise.all([
      fetch(`${BASE_URL}/dashboard/metrics`),
      fetch(`${BASE_URL}/dashboard/trend`)
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
      f1Score,
      datasetSize: metrics.dataset_size ?? 1000,
      modelType: metrics.model_type || 'Fine-tuned BERT with Custom Classification Head',
      categories: metrics.categories || ['Road Infrastructure', 'Water Supply', 'Waste Management', 'Sanitation', 'Street Lighting', 'Public Works'],
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
    const response = await fetch(`${BASE_URL}/executive/summary`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getWardHealth: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/executive/ward-health`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },
  getDeptWorkload: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/executive/department-workload`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  login: async (email: string, password: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.detail || 'Login failed');
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
    const response = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.detail || 'Registration failed');
    }
    return response.json();
  },

  getMe: async (token: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error('Failed to fetch user profile');
    }
    return response.json();
  },

  updateProfile: async (data: any, token: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/auth/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.detail || 'Failed to update profile');
    }
    return response.json();
  },

  getMyComplaints: async (token: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/my`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  getComplaintDetail: async (complaintId: string, token: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/complaints/${complaintId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response.json();
  },

  get: async (endpoint: string, token: string): Promise<Response> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response;
  },

  post: async (endpoint: string, data: any, token: string): Promise<Response> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response;
  },

  getSystemHealth: async (token: string): Promise<any> => {
    const response = await api.get('/admin/system-health', token);
    return response.json();
  },

  getPredictionsSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/predictions/summary`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getPriorityRules: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/priority/rules`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getKnowledgeSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/knowledge/summary`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  getDecisionSupportSummary: async (): Promise<any> => {
    const response = await fetch(`${BASE_URL}/decision-support/summary`);
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  copilotChat: async (message: string, history: any[] = []): Promise<any> => {
    const response = await fetch(`${BASE_URL}/copilot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history })
    });
    if (!response.ok) throw new Error(await getErrorMessage(response));
    return response.json();
  },

  patch: async (endpoint: string, data: any, token: string): Promise<Response> => {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }
    return response;
  },
};
