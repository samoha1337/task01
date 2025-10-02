import React, { useState } from 'react';
import { Card, Typography, Upload, Button, Form, Input, Space, Alert, Progress, Divider, List, Tag } from 'antd';
import { InboxOutlined, UploadOutlined, FileTextOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { apiService, UploadResponse, BatchStatus } from '../services/api.ts';

const { Title, Text } = Typography;
const { Dragger } = Upload;
const { TextArea } = Input;

const UploadPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [form] = Form.useForm();

  const handleFileUpload = async (file: File) => {
    try {
      setLoading(true);
      setUploadResult(null);
      setBatchStatus(null);

      const result = await apiService.uploadFile(file);
      setUploadResult(result);

      // Начинаем отслеживание статуса
      if (result.batch_id) {
        trackBatchStatus(result.batch_id);
      }
    } catch (error) {
      console.error('Ошибка загрузки файла:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTextUpload = async (values: any) => {
    try {
      setLoading(true);
      setUploadResult(null);
      setBatchStatus(null);

      const messages = values.messages
        .split('\n')
        .map((line: string) => line.trim())
        .filter((line: string) => line.length > 0);

      const result = await apiService.uploadMessages(
        messages,
        'web_interface',
        values.batch_name
      );
      
      setUploadResult(result);

      // Начинаем отслеживание статуса
      if (result.batch_id) {
        trackBatchStatus(result.batch_id);
      }
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
    } finally {
      setLoading(false);
    }
  };

  const trackBatchStatus = async (batchId: string) => {
    const checkStatus = async () => {
      try {
        const status = await apiService.getBatchStatus(batchId);
        setBatchStatus(status);

        // Если обработка еще не завершена, продолжаем проверять
        if (status.status === 'processing' || status.status === 'uploading') {
          setTimeout(checkStatus, 2000); // Проверяем каждые 2 секунды
        }
      } catch (error) {
        console.error('Ошибка получения статуса пакета:', error);
      }
    };

    checkStatus();
  };

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.txt,.json,.csv,.xlsx,.xls',
    beforeUpload: (file: File) => {
      handleFileUpload(file);
      return false; // Предотвращаем автоматическую загрузку
    },
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'processing': return 'blue';
      case 'uploading': return 'orange';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'Завершено';
      case 'failed': return 'Ошибка';
      case 'processing': return 'Обработка';
      case 'uploading': return 'Загрузка';
      default: return status;
    }
  };

  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">
          Загрузка данных
        </Title>
        <div style={{ color: '#666', marginTop: '8px' }}>
          Загрузка и обработка сообщений о полетах БПЛА согласно Табелю Минтранса РФ
        </div>
      </div>

      {/* Информация о поддерживаемых форматах */}
      <Alert
        message="Поддерживаемые форматы"
        description={
          <div>
            <p><strong>Файлы:</strong> TXT (одно сообщение на строку), JSON (массив строк сообщений)</p>
            <p><strong>Текст:</strong> Сообщения в формате согласно Табелю, каждое с новой строки</p>
            <p><strong>Ограничения:</strong> Максимум 10 000 сообщений в одном пакете, размер файла до 10 МБ</p>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        {/* Загрузка файла */}
        <Card title="Загрузка файла" className="upload-form">
          <Dragger {...uploadProps} disabled={loading}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">
              Нажмите или перетащите файл для загрузки
            </p>
            <p className="ant-upload-hint">
              Поддерживаются файлы .txt и .json с сообщениями о полетах
            </p>
          </Dragger>
        </Card>

        {/* Загрузка текста */}
        <Card title="Ввод сообщений" className="upload-form">
          <Form
            form={form}
            layout="vertical"
            onFinish={handleTextUpload}
          >
            <Form.Item
              name="batch_name"
              label="Название пакета (необязательно)"
            >
              <Input placeholder="Например: Полеты_01_10_2025" />
            </Form.Item>

            <Form.Item
              name="messages"
              label="Сообщения о полетах"
              rules={[{ required: true, message: 'Введите сообщения' }]}
            >
              <TextArea
                rows={8}
                placeholder="Введите сообщения, каждое с новой строки..."
              />
            </Form.Item>

            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                icon={<UploadOutlined />}
                loading={loading}
                block
              >
                Загрузить сообщения
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>

      {/* Результат загрузки */}
      {uploadResult && (
        <Card title="Результат загрузки" style={{ marginBottom: '24px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>ID пакета:</Text> <Text code>{uploadResult.batch_id}</Text>
            </div>
            <div>
              <Text strong>Статус:</Text> <Tag color={getStatusColor(uploadResult.status)}>{uploadResult.status}</Tag>
            </div>
            <div>
              <Text strong>Сообщений загружено:</Text> {uploadResult.total_messages}
            </div>
            <div>
              <Text>{uploadResult.message}</Text>
            </div>
          </Space>
        </Card>
      )}

      {/* Статус обработки */}
      {batchStatus && (
        <Card title="Статус обработки" style={{ marginBottom: '24px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>Файл:</Text> {batchStatus.filename}
            </div>
            <div>
              <Text strong>Статус:</Text> 
              <Tag color={getStatusColor(batchStatus.status)} style={{ marginLeft: '8px' }}>
                {getStatusText(batchStatus.status)}
              </Tag>
            </div>

            {/* Прогресс обработки */}
            {batchStatus.status === 'processing' && (
              <div>
                <Text strong>Прогресс обработки:</Text>
                <Progress 
                  percent={Math.round((batchStatus.processed_records / batchStatus.total_records) * 100)}
                  status="active"
                  format={(percent) => `${batchStatus.processed_records} из ${batchStatus.total_records}`}
                />
              </div>
            )}

            {/* Результаты обработки */}
            {batchStatus.status === 'completed' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                <div style={{ textAlign: 'center', padding: '16px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '6px' }}>
                  <div style={{ fontSize: '24px', color: '#52c41a', marginBottom: '8px' }}>
                    <CheckCircleOutlined />
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#52c41a' }}>
                    {batchStatus.valid_records}
                  </div>
                  <div style={{ color: '#52c41a' }}>Валидных записей</div>
                </div>

                <div style={{ textAlign: 'center', padding: '16px', background: '#fff2e8', border: '1px solid #ffbb96', borderRadius: '6px' }}>
                  <div style={{ fontSize: '24px', color: '#fa8c16', marginBottom: '8px' }}>
                    <FileTextOutlined />
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#fa8c16' }}>
                    {batchStatus.processed_records}
                  </div>
                  <div style={{ color: '#fa8c16' }}>Обработано</div>
                </div>

                {batchStatus.invalid_records > 0 && (
                  <div style={{ textAlign: 'center', padding: '16px', background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: '6px' }}>
                    <div style={{ fontSize: '24px', color: '#ff4d4f', marginBottom: '8px' }}>
                      <CloseCircleOutlined />
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#ff4d4f' }}>
                      {batchStatus.invalid_records}
                    </div>
                    <div style={{ color: '#ff4d4f' }}>С ошибками</div>
                  </div>
                )}
              </div>
            )}

            {/* Ошибка обработки */}
            {batchStatus.status === 'failed' && batchStatus.error_message && (
              <Alert
                message="Ошибка обработки"
                description={batchStatus.error_message}
                type="error"
                showIcon
              />
            )}

            {/* Время обработки */}
            {batchStatus.processing_end_time && (
              <div>
                <Text strong>Время обработки:</Text>
                <div>
                  Начало: {new Date(batchStatus.processing_start_time!).toLocaleString('ru-RU')}
                </div>
                <div>
                  Окончание: {new Date(batchStatus.processing_end_time).toLocaleString('ru-RU')}
                </div>
              </div>
            )}
          </Space>
        </Card>
      )}

      {/* Примеры сообщений */}
      <Card title="Примеры сообщений">
        <div style={{ marginBottom: '16px' }}>
          <Text strong>Примеры формата сообщений согласно Табелю Минтранса РФ:</Text>
        </div>
        
        <List
          size="small"
          bordered
          dataSource={[
            'FPL-UAV001-QUAD-UUDD1200-N0100F050 DCT UUEE-DOF/251015',
            'DEP-UAV002-HELI-UUDD1205-ACTUAL DEPARTURE TIME',
            'ARR-UAV001-QUAD-UUEE1245-ARRIVAL COMPLETED',
            'CHG-UAV003-FIXW-UUDD1300-ROUTE CHANGE DCT UUWW'
          ]}
          renderItem={(item) => (
            <List.Item>
              <Text code style={{ fontSize: '12px' }}>{item}</Text>
            </List.Item>
          )}
        />

        <Divider />

        <div style={{ fontSize: '14px', color: '#666' }}>
          <p><strong>Расшифровка полей:</strong></p>
          <ul>
            <li><strong>FPL/DEP/ARR/CHG</strong> - тип сообщения (план полета, вылет, прилет, изменение)</li>
            <li><strong>UAV001</strong> - идентификатор полета</li>
            <li><strong>QUAD/HELI/FIXW</strong> - тип БПЛА</li>
            <li><strong>UUDD1200</strong> - аэродром и время (ICAO код + HHMM)</li>
            <li><strong>N0100F050</strong> - скорость и эшелон</li>
            <li><strong>DCT UUEE</strong> - маршрут до аэродрома назначения</li>
          </ul>
        </div>
      </Card>
    </div>
  );
};

export default UploadPage;

