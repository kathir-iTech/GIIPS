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

export interface Incident {
  id: string;
  incident_number: string;
  category: string;
  cluster_size: number;
  ward: string;
  days_open: number;
  priority_score: number;
  priority_label: 'Critical' | 'High' | 'Medium' | 'Low';
  recommended_action: string;
  summary: string;
  complaints: Complaint[];
  status: string;
}

export interface Complaint {
  id: string;
  complaint_number: string;
  text: string;
  similarity_score: number;
  date_received: string;
}

export interface ClassificationMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  categoryDistribution: { category: string; count: number; percentage: number; }[];
  confusionMatrix: number[][];
  categories: string[];
  trendData: { month: string; accuracy: number; precision: number; recall: number; }[];
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
  clusterReasoning: string;
  similarity_threshold: number;
  summary: string;
}

export type SortDirection = 'asc' | 'desc';
export type SortField = 'priority_score' | 'cluster_size' | 'days_open' | 'category' | 'incident_number' | 'ward';
