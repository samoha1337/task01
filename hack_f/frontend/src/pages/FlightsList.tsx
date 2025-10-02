import React, { useState, useEffect } from 'react';
import { Table, Card, Form, Input, Select, DatePicker, Button, Space, Typography, Tag, Tooltip } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { apiService, Flight, FlightSearchParams } from '../services/api.ts';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const FlightsList: React.FC = () => {
  const [flights, setFlights] = useState<Flight[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [form] = Form.useForm();

  useEffect(() => {
    loadFlights();
  }, [pagination.current, pagination.pageSize]);

  const loadFlights = async (searchParams?: FlightSearchParams) => {
    try {
      setLoading(true);
      
      const params: FlightSearchParams = {
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
        ...searchParams,
      };

      const response = await apiService.searchFlights(params);
      setFlights(response.flights);
      setTotal(response.total);
    } catch (error) {
      console.error('Ошибка загрузки полетов:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (values: any) => {
    const searchParams: FlightSearchParams = {};
    
    if (values.flight_id) {
      searchParams.flight_id = values.flight_id;
    }
    if (values.aircraft_type) {
      searchParams.aircraft_type = values.aircraft_type;
    }
    if (values.region_departure) {
      searchParams.region_departure = values.region_departure;
    }
    if (values.region_arrival) {
      searchParams.region_arrival = values.region_arrival;
    }
    if (values.dateRange && values.dateRange.length === 2) {
      searchParams.date_from = values.dateRange[0].format('YYYY-MM-DD');
      searchParams.date_to = values.dateRange[1].format('YYYY-MM-DD');
    }

    setPagination({ current: 1, pageSize: pagination.pageSize });
    loadFlights(searchParams);
  };

  const handleReset = () => {
    form.resetFields();
    setPagination({ current: 1, pageSize: pagination.pageSize });
    loadFlights();
  };

  const columns = [
    {
      title: 'ID полета',
      dataIndex: 'flight_id',
      key: 'flight_id',
      width: 120,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: 'Тип БПЛА',
      dataIndex: 'aircraft_type',
      key: 'aircraft_type',
      width: 100,
      render: (text: string) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: 'Время вылета',
      dataIndex: 'departure_time',
      key: 'departure_time',
      width: 150,
      render: (text: string) => text ? dayjs(text).format('DD.MM.YYYY HH:mm') : '-',
    },
    {
      title: 'Время прилета',
      dataIndex: 'arrival_time',
      key: 'arrival_time',
      width: 150,
      render: (text: string) => text ? dayjs(text).format('DD.MM.YYYY HH:mm') : '-',
    },
    {
      title: 'Продолжительность',
      dataIndex: 'duration_minutes',
      key: 'duration_minutes',
      width: 120,
      render: (minutes: number) => {
        if (!minutes) return '-';
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours}ч ${mins}м`;
      },
    },
    {
      title: 'Регион вылета',
      dataIndex: 'region_departure',
      key: 'region_departure',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: 'Регион прилета',
      dataIndex: 'region_arrival',
      key: 'region_arrival',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: 'Расстояние',
      dataIndex: 'distance_km',
      key: 'distance_km',
      width: 100,
      render: (km: number) => km ? `${km.toFixed(1)} км` : '-',
    },
    {
      title: 'Статус',
      dataIndex: 'is_valid',
      key: 'is_valid',
      width: 80,
      render: (isValid: boolean) => (
        <Tag color={isValid ? 'green' : 'red'}>
          {isValid ? 'Валидный' : 'Ошибка'}
        </Tag>
      ),
    },
  ];

  const handleTableChange = (paginationConfig: any) => {
    setPagination({
      current: paginationConfig.current,
      pageSize: paginationConfig.pageSize,
    });
  };

  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">
          Полеты БПЛА
        </Title>
        <div style={{ color: '#666', marginTop: '8px' }}>
          Просмотр и поиск данных о полетах беспилотных авиационных систем
        </div>
      </div>

      {/* Форма поиска */}
      <Card style={{ marginBottom: '16px' }}>
        <Form
          form={form}
          layout="inline"
          onFinish={handleSearch}
          style={{ flexWrap: 'wrap', gap: '8px' }}
        >
          <Form.Item name="flight_id" style={{ marginBottom: '8px' }}>
            <Input 
              placeholder="ID полета" 
              style={{ width: 150 }}
              allowClear
            />
          </Form.Item>
          
          <Form.Item name="aircraft_type" style={{ marginBottom: '8px' }}>
            <Select
              placeholder="Тип БПЛА"
              style={{ width: 150 }}
              allowClear
            >
              <Select.Option value="QUAD">QUAD</Select.Option>
              <Select.Option value="HEXA">HEXA</Select.Option>
              <Select.Option value="OCTO">OCTO</Select.Option>
              <Select.Option value="FIXW">FIXW</Select.Option>
              <Select.Option value="HELI">HELI</Select.Option>
              <Select.Option value="UNKN">UNKN</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="region_departure" style={{ marginBottom: '8px' }}>
            <Input 
              placeholder="Регион вылета" 
              style={{ width: 180 }}
              allowClear
            />
          </Form.Item>
          
          <Form.Item name="region_arrival" style={{ marginBottom: '8px' }}>
            <Input 
              placeholder="Регион прилета" 
              style={{ width: 180 }}
              allowClear
            />
          </Form.Item>
          
          <Form.Item name="dateRange" style={{ marginBottom: '8px' }}>
            <RangePicker
              placeholder={['Дата от', 'Дата до']}
              format="DD.MM.YYYY"
              style={{ width: 250 }}
            />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: '8px' }}>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit" 
                icon={<SearchOutlined />}
                loading={loading}
              >
                Найти
              </Button>
              <Button onClick={handleReset} icon={<ReloadOutlined />}>
                Сбросить
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Таблица полетов */}
      <Card>
        <Table
          columns={columns}
          dataSource={flights}
          rowKey="id"
          loading={loading}
          className="flights-table"
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} из ${total} полетов`,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default FlightsList;

