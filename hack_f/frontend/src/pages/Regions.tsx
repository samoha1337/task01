import React, { useState, useEffect } from 'react';
import { Typography, Card, Table, Input, Button, Space, Form, Alert, message } from 'antd';
import { SearchOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { apiService, Region, GeocodeResult } from '../services/api.ts';

const { Title } = Typography;

const Regions: React.FC = () => {
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<GeocodeResult | null>(null);
  const [geocodeLoading, setGeocodeLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRegions();
  }, []);

  const loadRegions = async () => {
    try {
      setLoading(true);
      const response = await apiService.getRegions();
      setRegions(response.regions);
    } catch (error) {
      console.error('Ошибка загрузки регионов:', error);
      message.error('Не удалось загрузить список регионов');
    } finally {
      setLoading(false);
    }
  };

  const handleGeocode = async (values: any) => {
    try {
      setGeocodeLoading(true);
      const result = await apiService.geocodeCoordinates(values.latitude, values.longitude);
      setGeocodeResult(result);
      
      if (result.region_name) {
        message.success(`Координаты привязаны к региону: ${result.region_name}`);
      } else {
        message.warning('Регион не найден для указанных координат');
      }
    } catch (error) {
      console.error('Ошибка геопривязки:', error);
      message.error('Ошибка определения региона');
    } finally {
      setGeocodeLoading(false);
    }
  };

  const columns = [
    {
      title: 'Код',
      dataIndex: 'region_code',
      key: 'region_code',
      width: 80,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: 'Федеральный округ',
      dataIndex: 'federal_district',
      key: 'federal_district',
      width: 200,
      render: (text: string) => text || '-',
    },
    {
      title: 'Тип',
      dataIndex: 'region_type',
      key: 'region_type',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: 'Площадь (км²)',
      dataIndex: 'area_sq_km',
      key: 'area_sq_km',
      width: 120,
      render: (area: number) => area ? area.toLocaleString('ru-RU') : '-',
    },
  ];

  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">
          Регионы РФ
        </Title>
        <div style={{ color: '#666', marginTop: '8px' }}>
          Субъекты Российской Федерации и геопривязка координат
        </div>
      </div>

      {/* Геопривязка координат */}
      <Card title="Геопривязка координат" style={{ marginBottom: '16px' }}>
        <Form
          form={form}
          layout="inline"
          onFinish={handleGeocode}
          style={{ marginBottom: '16px' }}
        >
          <Form.Item
            name="latitude"
            label="Широта"
            rules={[
              { required: true, message: 'Введите широту' },
              { type: 'number', min: -90, max: 90, message: 'Широта должна быть от -90 до 90' }
            ]}
          >
            <Input 
              placeholder="55.7558" 
              style={{ width: 120 }}
              type="number"
              step="0.000001"
            />
          </Form.Item>

          <Form.Item
            name="longitude"
            label="Долгота"
            rules={[
              { required: true, message: 'Введите долготу' },
              { type: 'number', min: -180, max: 180, message: 'Долгота должна быть от -180 до 180' }
            ]}
          >
            <Input 
              placeholder="37.6173" 
              style={{ width: 120 }}
              type="number"
              step="0.000001"
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              icon={<EnvironmentOutlined />}
              loading={geocodeLoading}
            >
              Определить регион
            </Button>
          </Form.Item>
        </Form>

        {geocodeResult && (
          <Alert
            message={geocodeResult.region_name ? "Регион определен" : "Регион не найден"}
            description={
              geocodeResult.region_name ? (
                <div>
                  <p><strong>Регион:</strong> {geocodeResult.region_name}</p>
                  <p><strong>Код:</strong> {geocodeResult.region_code}</p>
                  {geocodeResult.federal_district && (
                    <p><strong>Федеральный округ:</strong> {geocodeResult.federal_district}</p>
                  )}
                  {geocodeResult.region_type && (
                    <p><strong>Тип:</strong> {geocodeResult.region_type}</p>
                  )}
                  <p><strong>Координаты:</strong> {geocodeResult.latitude}, {geocodeResult.longitude}</p>
                </div>
              ) : (
                <div>
                  <p>Координаты {geocodeResult.latitude}, {geocodeResult.longitude} не принадлежат ни одному региону РФ</p>
                  {geocodeResult.message && <p>{geocodeResult.message}</p>}
                </div>
              )
            }
            type={geocodeResult.region_name ? "success" : "warning"}
            showIcon
            style={{ marginTop: '16px' }}
          />
        )}
      </Card>

      {/* Список регионов */}
      <Card 
        title="Субъекты Российской Федерации"
        extra={
          <Button 
            icon={<SearchOutlined />}
            onClick={loadRegions}
            loading={loading}
          >
            Обновить
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={regions}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} из ${total} регионов`,
            pageSizeOptions: ['20', '50', '100'],
            defaultPageSize: 20,
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      {/* Информация о данных */}
      <Card title="О данных" style={{ marginTop: '16px' }}>
        <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
          <p>
            <strong>Источник данных:</strong> Официальные шейп-файлы границ субъектов 
            Российской Федерации от Федеральной службы государственной регистрации, 
            кадастра и картографии (Росреестр).
          </p>
          <p>
            <strong>Система координат:</strong> WGS84 (EPSG:4326) - всемирная геодезическая 
            система координат, используемая в GPS.
          </p>
          <p>
            <strong>Точность геопривязки:</strong> Определение региона производится строго 
            по границам без буферов и допусков, в соответствии с официальными данными.
          </p>
          <p>
            <strong>Обновление данных:</strong> Шейп-файлы обновляются ежемесячно согласно 
            регламенту системы.
          </p>
        </div>
      </Card>
    </div>
  );
};

export default Regions;

