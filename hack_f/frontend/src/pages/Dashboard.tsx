import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Spin, Alert } from 'antd';
import {
  SendOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { apiService } from '../services/api.ts';

const { Title } = Typography;

interface DashboardStats {
  totalFlights: number;
  averageDuration: number;
  topRegions: Array<{ region: string; flights: number }>;
  aircraftTypes: Record<string, number>;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Загрузка статистики полетов
      const response = await apiService.getFlightsSummary();
      
      setStats({
        totalFlights: response.total_flights || 0,
        averageDuration: response.average_duration_minutes || 0,
        topRegions: response.top_regions || [],
        aircraftTypes: response.aircraft_types || {}
      });
    } catch (err) {
      console.error('Ошибка загрузки данных панели управления:', err);
      setError('Не удалось загрузить данные. Проверьте подключение к серверу.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>Загрузка данных...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Ошибка загрузки данных"
        description={error}
        type="error"
        showIcon
        action={
          <button onClick={loadDashboardData} style={{ border: 'none', background: 'none', color: '#1890ff', cursor: 'pointer' }}>
            Повторить попытку
          </button>
        }
      />
    );
  }

  // Подготовка данных для графиков
  const regionChartData = stats?.topRegions?.map(item => ({
    name: item.region,
    flights: item.flights
  })) || [];

  const aircraftChartData = Object.entries(stats?.aircraftTypes || {}).map(([type, count]) => ({
    name: type,
    value: count
  }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">
          Панель управления
        </Title>
        <div style={{ color: '#666', marginTop: '8px' }}>
          Обзор активности полетов БПЛА в Российской Федерации
        </div>
      </div>

      {/* Основная статистика */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Всего полетов"
              value={stats?.totalFlights || 0}
              prefix={<SendOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Средняя продолжительность"
              value={stats?.averageDuration || 0}
              suffix="мин"
              prefix={<ClockCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
              precision={1}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Активных регионов"
              value={stats?.topRegions?.length || 0}
              prefix={<GlobalOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Типов БПЛА"
              value={Object.keys(stats?.aircraftTypes || {}).length}
              prefix={<RiseOutlined style={{ color: '#f5222d' }} />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Графики */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card 
            title="Топ-10 регионов по количеству полетов" 
            className="dashboard-card"
          >
            <div style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={regionChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name" 
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    fontSize={12}
                  />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="flights" fill="#1890ff" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={10}>
          <Card 
            title="Распределение по типам БПЛА" 
            className="dashboard-card"
          >
            <div style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={aircraftChartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {aircraftChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Информационные блоки */}
      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} md={12}>
          <Card 
            title="О системе" 
            className="dashboard-card"
          >
            <Space direction="vertical" size="middle">
              <div>
                <strong>Назначение:</strong> Система предназначена для обработки и анализа 
                данных о полетах беспилотных авиационных систем (БАС) на территории 
                Российской Федерации.
              </div>
              <div>
                <strong>Нормативная база:</strong> Система соответствует требованиям 
                «Табеля сообщений о движении воздушных судов в Российской Федерации», 
                утвержденного приказом Минтранса России от 24 января 2013 года №13.
              </div>
              <div>
                <strong>Функциональность:</strong> Парсинг телеграмм, геопривязка к субъектам РФ, 
                аналитика полетов, генерация отчетов.
              </div>
            </Space>
          </Card>
        </Col>
        
        <Col xs={24} md={12}>
          <Card 
            title="Последние обновления" 
            className="dashboard-card"
          >
            <Space direction="vertical" size="middle">
              <div>
                <strong>Система запущена:</strong> Базовая функциональность системы 
                готова к использованию. Доступны основные модули обработки данных.
              </div>
              <div>
                <strong>Доступные функции:</strong>
                <ul style={{ marginTop: '8px', paddingLeft: '20px' }}>
                  <li>Загрузка и парсинг сообщений</li>
                  <li>Валидация и очистка данных</li>
                  <li>Геопривязка к регионам РФ</li>
                  <li>Просмотр полетов</li>
                  <li>Базовая аналитика</li>
                </ul>
              </div>
              <div>
                <strong>В разработке:</strong> Расширенная аналитика, генерация отчетов, 
                автоматическое обновление шейп-файлов.
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;

