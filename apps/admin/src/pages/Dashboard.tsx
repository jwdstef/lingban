import { Card, Col, Row, Statistic } from 'antd';
import {
  UserOutlined,
  MessageOutlined,
  RobotOutlined,
  HeartOutlined,
} from '@ant-design/icons';

export default function Dashboard() {
  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日活跃用户"
              value={128}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#8B5CF6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日消息数"
              value={3456}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#10B981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃角色"
              value={3}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#F59E0B' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="主动关怀次数"
              value={89}
              prefix={<HeartOutlined />}
              valueStyle={{ color: '#EF4444' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="用户留存趋势">
            <p style={{ color: '#999' }}>图表区域 - 接入 ECharts/AntV</p>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="情绪分布">
            <p style={{ color: '#999' }}>图表区域 - 用户情绪统计</p>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
