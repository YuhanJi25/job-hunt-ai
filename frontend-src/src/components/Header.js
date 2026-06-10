import React from 'react';
import { Layout, Button, Space } from 'antd';
import { Link, useNavigate } from 'react-router-dom';
import { 
  LoginOutlined,
  UserAddOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Header: AntHeader } = Layout;

const Header = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  return (
    <AntHeader style={{ 
      background: 'white', 
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: '64px'
    }}>
      <Link to="/" style={{ 
        fontSize: '20px', 
        fontWeight: 'bold', 
        color: '#1890ff',
        textDecoration: 'none'
      }}>
        🚀 JobMatch AI
      </Link>
      
      {!isAuthenticated() && (
        <Space>
          <Button 
            type="text" 
            icon={<LoginOutlined />}
            onClick={() => navigate('/login')}
          >
            Login
          </Button>
          <Button 
            type="primary" 
            icon={<UserAddOutlined />}
            onClick={() => navigate('/register')}
          >
            Sign Up
          </Button>
        </Space>
      )}
    </AntHeader>
  );
};

export default Header;
