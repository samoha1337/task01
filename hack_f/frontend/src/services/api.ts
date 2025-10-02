/**
 * API сервис для взаимодействия с backend системы отслеживания полетов БПЛА
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Базовая конфигурация API
const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Создание экземпляра axios
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Перехватчик запросов
apiClient.interceptors.request.use(
  (config) => {
    // Добавление токена авторизации, если есть
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Перехватчик ответов
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Очистка токена при ошибке авторизации
      localStorage.removeItem('authToken');
    }
    return Promise.reject(error);
  }
);

// Интерфейсы для типизации данных
export interface Flight {
  id: string;
  flight_id: string;
  aircraft_type?: string;
  aircraft_registration?: string;
  departure_time?: string;
  arrival_time?: string;
  duration_minutes?: number;
  departure_coordinates?: [number, number];
  arrival_coordinates?: [number, number];
  region_departure?: string;
  region_arrival?: string;
  altitude_max?: number;
  distance_km?: number;
  operator_name?: string;
  flight_purpose?: string;
  is_valid: boolean;
  created_at: string;
}

export interface FlightSearchParams {
  flight_id?: string;
  aircraft_type?: string;
  region_departure?: string;
  region_arrival?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface FlightSearchResponse {
  flights: Flight[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface FlightsSummary {
  total_flights: number;
  average_duration_minutes?: number;
  aircraft_types: Record<string, number>;
  top_regions: Array<{ region: string; flights: number }>;
  period?: {
    from?: string;
    to?: string;
  };
}

export interface UploadResponse {
  batch_id: string;
  status: string;
  message: string;
  total_messages: number;
  processing_started: boolean;
}

export interface BatchStatus {
  batch_id: string;
  status: string;
  filename: string;
  total_records: number;
  processed_records: number;
  valid_records: number;
  invalid_records: number;
  upload_time: string;
  processing_start_time?: string;
  processing_end_time?: string;
  error_message?: string;
}

export interface Region {
  id: string;
  name: string;
  region_code: string;
  federal_district?: string;
  region_type?: string;
  area_sq_km?: number;
}

export interface GeocodeResult {
  latitude: number;
  longitude: number;
  region_code?: string;
  region_name?: string;
  federal_district?: string;
  region_type?: string;
  message?: string;
}

// API методы
class ApiService {
  // Полеты
  async searchFlights(params: FlightSearchParams): Promise<FlightSearchResponse> {
    const response = await apiClient.get('/flights', { params });
    return response.data;
  }

  async getFlight(flightId: string): Promise<Flight> {
    const response = await apiClient.get(`/flights/${flightId}`);
    return response.data;
  }

  async getFlightsSummary(dateFrom?: string, dateTo?: string): Promise<FlightsSummary> {
    const params: any = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    
    const response = await apiClient.get('/flights/statistics/summary', { params });
    return response.data;
  }

  // Загрузка данных
  async uploadMessages(messages: string[], source?: string, batchName?: string): Promise<UploadResponse> {
    const data = {
      messages,
      source: source || 'web_interface',
      batch_name: batchName
    };
    const response = await apiClient.post('/upload/messages', data);
    return response.data;
  }

  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getBatchStatus(batchId: string): Promise<BatchStatus> {
    const response = await apiClient.get(`/upload/batch/${batchId}/status`);
    return response.data;
  }

  async getBatches(limit = 50, offset = 0, status?: string): Promise<{ batches: BatchStatus[] }> {
    const params: any = { limit, offset };
    if (status) params.status = status;
    
    const response = await apiClient.get('/upload/batches', { params });
    return response.data;
  }

  // Регионы
  async getRegions(federalDistrict?: string, regionType?: string, limit = 100, offset = 0): Promise<{ regions: Region[] }> {
    const params: any = { limit, offset };
    if (federalDistrict) params.federal_district = federalDistrict;
    if (regionType) params.region_type = regionType;
    
    const response = await apiClient.get('/regions', { params });
    return response.data;
  }

  async geocodeCoordinates(latitude: number, longitude: number): Promise<GeocodeResult> {
    const response = await apiClient.get('/regions/geocode', {
      params: { latitude, longitude }
    });
    return response.data;
  }

  // Аналитика
  async getRegionalMetrics(regionCode?: string, dateFrom?: string, dateTo?: string): Promise<any> {
    const params: any = {};
    if (regionCode) params.region_code = regionCode;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    
    const response = await apiClient.get('/analytics/metrics/regions', { params });
    return response.data;
  }

  async getRegionsRanking(period = 'month', limit = 20): Promise<any> {
    const response = await apiClient.get('/analytics/ranking', {
      params: { period, limit }
    });
    return response.data;
  }

  // Отчеты
  async generateReport(reportType: string, format: string, params: any): Promise<any> {
    const data = {
      report_type: reportType,
      format: format,
      ...params
    };
    const response = await apiClient.post('/reports/generate', data);
    return response.data;
  }

  async getReportStatus(reportId: string): Promise<any> {
    const response = await apiClient.get(`/reports/${reportId}/status`);
    return response.data;
  }

  async downloadReport(reportId: string): Promise<any> {
    const response = await apiClient.get(`/reports/${reportId}/download`);
    return response.data;
  }

  // Системная информация
  async getSystemInfo(): Promise<any> {
    const response = await apiClient.get('/info', { baseURL: BASE_URL.replace('/api/v1', '') });
    return response.data;
  }

  async getHealthCheck(): Promise<any> {
    const response = await apiClient.get('/health', { baseURL: BASE_URL.replace('/api/v1', '') });
    return response.data;
  }
}

// Экспорт экземпляра сервиса
export const apiService = new ApiService();
export default apiService;

