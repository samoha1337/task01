import React from 'react';
import { Typography, Card, Alert } from 'antd';

const { Title } = Typography;

const Analytics: React.FC = () => {
  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">
          Аналитика
        </Title>
        <div style={{ color: '#666', marginTop: '8px' }}>
          Расширенная аналитика и метрики полетов БПЛА
        </div>
      </div>

      <Alert
        message="Модуль аналитики в разработке"
        description="Расширенные аналитические функции будут доступны в следующей версии системы. Базовая статистика доступна на главной странице."
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Card title="Планируемые функции аналитики">
        <ul>
          <li>Региональные метрики активности БПЛА</li>
          <li>Временные тренды и сезонность</li>
          <li>Анализ плотности полетов по территории</li>
          <li>Сравнительный анализ регионов</li>
          <li>Прогнозирование активности</li>
          <li>Анализ маршрутов полетов</li>
          <li>Статистика по типам БПЛА</li>
          <li>Операторская аналитика</li>
        </ul>
      </Card>
    </div>
  );
};

export default Analytics;

