const DB_NAME = 'giips-offline-queue';
const DB_VERSION = 1;
const STORE_NAME = 'complaints';

const openDB = (): Promise<IDBDatabase> =>
  new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

export interface OfflineComplaint {
  id: number;
  title: string;
  description: string;
  location: string;
  ward: string;
  address: string;
  latitude: number;
  longitude: number;
  full_name: string;
  email: string;
  predicted_category?: string;
  tags?: string[];
  created_at: string;
  status: 'pending';
}

export const saveOfflineComplaint = async (data: Omit<OfflineComplaint, 'id' | 'created_at' | 'status'>): Promise<void> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.add({
      ...data,
      id: Date.now(),
      created_at: new Date().toISOString(),
      status: 'pending' as const,
    });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
};

export const getOfflineComplaints = async (): Promise<OfflineComplaint[]> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
};

export const removeOfflineComplaint = async (id: number): Promise<void> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
};

export const retryOfflineSubmissions = async (): Promise<void> => {
  if (!navigator.onLine) return;
  const complaints = await getOfflineComplaints();
  if (complaints.length === 0) return;

  const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';
  for (const complaint of complaints) {
    try {
      const res = await fetch(`${BASE_URL}/complaints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(complaint),
      });
      if (res.ok) {
        await removeOfflineComplaint(complaint.id);
      }
    } catch {
      // will retry next time
    }
  }
};

export const getOfflineCount = async (): Promise<number> => {
  const complaints = await getOfflineComplaints();
  return complaints.length;
};
