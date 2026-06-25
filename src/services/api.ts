import incidentsData from '../data/incidents.json';
import complaintsData from '../data/complaints.json';
import type { DashboardData, Incident, ClassificationMetrics, ClusterDetail } from '../types';

const incidents: Incident[] = incidentsData.map(incident => ({
  ...incident,
  priority_label: incident.priority_label as 'Critical' | 'High' | 'Medium' | 'Low',
  complaints: complaintsData
    .filter(c => c.incident_id === incident.id)
    .map(c => ({
      id: c.id,
      complaint_number: c.complaint_number,
      text: c.text,
      similarity_score: c.similarity_score,
      date_received: c.date_received
    }))
}));

export const api = {
  getDashboardData: async (): Promise<DashboardData> => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 200));

    const totalComplaints = complaintsData.length;
    const uniqueIncidents = incidentsData.length;
    const criticalIncidents = incidentsData.filter(i => i.priority_label === 'Critical').length;
    const highPriorityIncidents = incidentsData.filter(i => i.priority_label === 'High').length;
    const avgResolutionScore = Math.round(
      incidentsData.reduce((sum, i) => sum + i.priority_score, 0) / incidentsData.length
    );
    const workloadReduction = Math.round(((totalComplaints - uniqueIncidents) / totalComplaints) * 100 * 10) / 10;

    // Generate trend data (last 6 months)
    const trendData = [];
    for (let i = 5; i >= 0; i--) {
      const date = new Date();
      date.setMonth(date.getMonth() - i);
      const monthStr = date.toISOString().substring(0, 7);
      trendData.push({
        date: monthStr,
        complaints: Math.floor(Math.random() * 200) + 100,
        incidents: Math.floor(Math.random() * 40) + 15
      });
    }

    return {
      totalComplaints,
      uniqueIncidents,
      workloadReduction,
      criticalIncidents,
      highPriorityIncidents,
      avgResolutionScore,
      trendData,
      beforeAfter: {
        before: totalComplaints,
        after: uniqueIncidents,
        reduction: workloadReduction
      }
    };
  },

  getIncidents: async (_sort: string = 'priority'): Promise<Incident[]> => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300));
    return incidents.sort((a, b) => b.priority_score - a.priority_score);
  },

  getClassificationMetrics: async (): Promise<ClassificationMetrics> => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 200));

    const categoryMap = new Map<string, number>();
    incidentsData.forEach(item => {
      categoryMap.set(item.category, (categoryMap.get(item.category) || 0) + item.cluster_size);
    });

    const total = Array.from(categoryMap.values()).reduce((a, b) => a + b, 0);
    const categoryDistribution = Array.from(categoryMap.entries()).map(([category, count]) => ({
      category,
      count,
      percentage: Math.round((count / total) * 100 * 10) / 10
    })).sort((a, b) => b.count - a.count);

    const categories = categoryDistribution.map(c => c.category);

    const confusionMatrix = categories.map((_, i) =>
      categories.map((_, j) =>
        i === j ? Math.floor(Math.random() * 100) + 200 : Math.floor(Math.random() * 20)
      )
    );

    const trendData = [];
    for (let i = 5; i >= 0; i--) {
      const date = new Date();
      date.setMonth(date.getMonth() - i);
      const monthStr = date.toISOString().substring(0, 7);
      trendData.push({
        month: monthStr,
        accuracy: 0.87 + Math.random() * 0.05,
        precision: 0.86 + Math.random() * 0.05,
        recall: 0.88 + Math.random() * 0.05
      });
    }

    return {
      accuracy: 0.923,
      precision: 0.917,
      recall: 0.931,
      f1Score: 0.924,
      categoryDistribution,
      confusionMatrix,
      categories,
      trendData,
      datasetSize: complaintsData.length,
      modelType: 'Fine-tuned BERT with Custom Classification Head'
    };
  },

  getClusterDetail: async (incidentId: string): Promise<ClusterDetail> => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 250));

    const incident = incidentsData.find(i => i.id === incidentId);
    if (!incident) {
      throw new Error('Incident not found');
    }

    const incidentComplaints = complaintsData
      .filter(c => c.incident_id === incidentId)
      .sort((a, b) => b.similarity_score - a.similarity_score);

    return {
      incident_id: incident.id,
      incident_number: incident.incident_number,
      category: incident.category,
      ward: incident.ward,
      cluster_size: incident.cluster_size,
      groupedInto: 1,
      summary: incident.summary,
      complaints: incidentComplaints.map(c => ({
        id: c.id,
        complaint_number: c.complaint_number,
        text: c.text,
        similarity_score: c.similarity_score,
        date_received: c.date_received
      })),
      clusterReasoning: incident.clustering_reasoning,
      similarity_threshold: incident.similarity_threshold
    };
  }
};
