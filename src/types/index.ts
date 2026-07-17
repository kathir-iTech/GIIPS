export interface DashboardData {
  totalComplaints: number;
  uniqueIncidents: number;
  workloadReduction: number;
  criticalIncidents: number;
  highPriorityIncidents: number;
  mediumPriorityIncidents: number;
  lowPriorityIncidents: number;
  avgResolutionScore: number;
  avgDaysOpen: number;
  trendData: { date: string; complaints: number; incidents: number; }[];
  beforeAfter: { before: number; after: number; reduction: number; };
  categoryBreakdown: { category: string; count: number; color: string; }[];
  wardBreakdown: { ward: string; count: number; }[];
  recentIncidents: Incident[];
}

export interface PriorityHistory {
  id: string;
  incident_id: string;
  old_score: number;
  new_score: number;
  reason: string;
  changed_at: string;
}

export interface Incident {
  id: string;
  incident_number: string;
  category: string;
  department?: string | null;
  cluster_size: number;
  ward: string;
  days_open: number;
  priority_score: number;
  priority_label: 'Critical' | 'High' | 'Medium' | 'Low';
  recommended_action: string;
  summary: string;
  complaints: Complaint[];
  status: string;
  priority_history: PriorityHistory[];
}

export interface Complaint {
  id: string;
  complaint_number: string;
  text: string;
  similarity_score: number;
  date_received: string;
  merge_reason?: string;
}

export interface ClassificationMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  categoryDistribution: { category: string; count: number; percentage: number; }[];
  confusionMatrix: number[][];
  categories: string[];
  trendData: { month: string; complaints: number; incidents: number; }[];
  datasetSize: number;
  modelType: string;
}

export interface ClusterDetail {
  incident_id: string;
  incident_number: string;
  category: string;
  ward: string;
  cluster_size: number;
  groupedInto: number;
  complaints: Complaint[];
  priority_history: PriorityHistory[];
  clusterReasoning: string;
  similarity_threshold: number;
  summary: string;
}

export type SortDirection = 'asc' | 'desc';
export type SortField = 'priority_score' | 'cluster_size' | 'days_open' | 'category' | 'incident_number' | 'ward';

export interface AssignedOfficer {
  name?: string | null;
  phone?: string | null;
  role?: string | null;
  zone_name?: string | null;
  corporation_id?: string | null;
  department?: string | null;
  category?: string | null;
  primary_role?: string | null;
  kml_id?: string | null;
  ward_name?: string | null;
  ward_number?: string | null;
  error?: string | null;
  fallback_reason?: string | null;
}

export interface CitizenComplaint {
  id: string;
  title: string;
  description: string;
  location: string;
  ward: string;
  predicted_category: string;
  department?: string | null;
  confidence: number;
  priority: string;
  similarity_score: number | null;
  merge_reason: string | null;
  date_received: string;
  image_path?: string | null;
  image_url?: string | null;
  assigned_officer?: AssignedOfficer | null;
  incident?: {
    id: string | null;
    incident_number: string | null;
    category: string | null;
    priority_label: string | null;
    status: string | null;
    cluster_size: number | null;
    recommended_action: string | null;
    summary: string | null;
    priority_history: Array<{
      id: string;
      old_score: number;
      new_score: number;
      reason: string;
      changed_at: string;
    }>;
  } | null;
}

export interface ComplaintDetail extends CitizenComplaint {}

export type UserRole = 'Citizen' | 'Officer' | 'Executive' | 'Councillor' | 'Commissioner' | 'MLA' | 'Collector';

export interface AppNotification {
  id: string;
  user_id: string;
  complaint_id: string | null;
  type: string;
  data: Record<string, any> | null;
  is_read: boolean;
  created_at: string;
}
