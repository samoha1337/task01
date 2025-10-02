import React, { useState } from 'react';
import { Layout as AntLayout, Menu, theme, Typography, Space, Divider } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  SendOutlined,
  BarChartOutlined,
  FileTextOutlined,
  UploadOutlined,
  GlobalOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Панель управления',
    },
    {
      key: '/flights',
      icon: <SendOutlined />,
      label: 'Полеты',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Аналитика',
    },
    {
      key: '/reports',
      icon: <FileTextOutlined />,
      label: 'Отчеты',
    },
    {
      key: '/upload',
      icon: <UploadOutlined />,
      label: 'Загрузка данных',
    },
    {
      key: '/regions',
      icon: <GlobalOutlined />,
      label: 'Регионы',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        style={{
          background: colorBgContainer,
          boxShadow: '2px 0 8px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ 
          padding: '16px', 
          textAlign: 'center',
          borderBottom: '1px solid #f0f0f0'
        }}>
          {!collapsed ? (
            <Space direction="vertical" size="small">
              <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                БПЛА Мониторинг
              </Title>
              <div style={{ fontSize: '12px', color: '#666' }}>
                Система отслеживания полетов
              </div>
            </Space>
          ) : (
            <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
              БМ
            </Title>
          )}
        </div>
        
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0, marginTop: '8px' }}
        />
      </Sider>
      
      <AntLayout>
        <Header style={{ 
          padding: '0 16px', 
          background: colorBgContainer,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <Space>
            {React.createElement(
              collapsed ? MenuUnfoldOutlined : MenuFoldOutlined,
              {
                className: 'trigger',
                onClick: () => setCollapsed(!collapsed),
                style: { 
                  fontSize: '18px',
                  cursor: 'pointer',
                  padding: '0 8px',
                  color: '#666'
                },
              },
            )}
            <Divider type="vertical" />
            <Title level={4} style={{ margin: 0, color: '#333' }}>
              {menuItems.find(item => item.key === location.pathname)?.label || 'Система отслеживания полетов БПЛА'}
            </Title>
          </Space>
          
          <Space>
            <div style={{ 
              fontSize: '14px', 
              color: '#666',
              textAlign: 'right'
            }}>
              <div>Версия 1.0.0</div>
              <div style={{ fontSize: '12px' }}>
                Соответствует приказу Минтранса РФ №13
              </div>
            </div>
          </Space>
        </Header>
        
        <Content
          style={{
            margin: '16px',
            padding: '24px',
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <div className="fade-in">
            {children}
          </div>
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;

