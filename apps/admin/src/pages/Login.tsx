import { LockOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Typography, message } from 'antd';
import axios from 'axios';
import { Navigate, useNavigate } from 'react-router-dom';

const { Text, Title } = Typography;

interface LoginFormValues {
  token: string;
}

export default function Login() {
  const navigate = useNavigate();
  const hasToken = Boolean(localStorage.getItem('admin_token'));

  if (hasToken) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleFinish = async (values: LoginFormValues) => {
    const token = values.token.trim();
    try {
      await axios.post(
        '/api/v1/admin/auth/verify',
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      );
      localStorage.setItem('admin_token', token);
      message.success('登录成功');
      navigate('/dashboard', { replace: true });
    } catch {
      message.error('管理员令牌无效');
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f7fb',
        padding: 24,
      }}
    >
      <Card style={{ width: 380, borderRadius: 8 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          灵伴管理后台
        </Title>
        <Text type="secondary">请输入管理员令牌</Text>
        <Form layout="vertical" onFinish={handleFinish}>
          <Form.Item
            name="token"
            label="管理员令牌"
            rules={[{ required: true, message: '请输入管理员令牌' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              autoFocus
              placeholder="Bearer token"
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
