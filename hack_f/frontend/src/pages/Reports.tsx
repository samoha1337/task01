import React from 'react';
import { Typography, Card, Alert } from 'antd';

const { Title } = Typography;

const Reports: React.FC = () => {
  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">
          Отчеты
        </Title>
        <div style={{ color: '#666', marginTop: '8px' }}>
          Генерация отчетов и экспорт данных
        </div>
      </div>

      <Alert
        message="Система генерации отчетов в разработке"
        description="Функции автоматической генерации отчетов и графиков будут доступны в следующей версии системы."
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Card title="Планируемые типы отчетов">
        <ul>
          <li>Сводные отчеты по полетам за период</li>
          <li>Региональная аналитика активности БПЛА</li>
          <li>Временные тренды и динамика</li>
          <li>Отчеты по типам воздушных судов</li>
          <li>Операторская отчетность</li>
          <li>Графические отчеты (PNG/JPEG)</li>
          <li>Экспорт в форматах JSON, CSV, XLSX</li>
          <li>Автоматическая отправка отчетов</li>
        </ul>
      </Card>
    </div>
  );
};

export default Reports;

