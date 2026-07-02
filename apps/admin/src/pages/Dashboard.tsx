import { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, message } from 'antd';
import {
  UserOutlined,
  MessageOutlined,
  RobotOutlined,
  HeartOutlined,
} from '@ant-design/icons';
import api from '../services/api';

interface Stats {
  total_users: number;
  today_active_users: number;
  total_messages: number;
  total_memories: number;
  character_distribution: Record<string, number>;
}

const CHARACTER_NAMES: Record<string, string> = {
  yinyue: '银月',
  babata: '巴巴塔',
  heihaung: '黑皇',
};

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/dashboard/stats');
      setStats(response.data);
    } catch (error) {
      message.error('加载统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  const activeCharacters = stats?.character_distribution
    ? Object.keys(stats.character_distribution).length
    : 0;

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="总用户数"
              value={stats?.total_users ?? 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#8B5CF6' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="今日活跃用户"
              value={stats?.today_active_users ?? 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#10B981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="消息总数"
              value={stats?.total_messages ?? 0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#F59E0B' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="记忆总数"
              value={stats?.total_memories ?? 0}
              prefix={<HeartOutlined />}
              valueStyle={{ color: '#EF4444' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="角色分布">
            {stats?.character_distribution ? (
              <div>
                {Object.entries(stats.character_distribution).map(([charId, count]) => (
                  <div key={charId} style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                    <span>{CHARACTER_NAMES[charId] || charId}</span>
                    <span style={{ color: '#8B5CF6', fontWeight: 500 }}>{count} 人</span>
                  </div>
                ))}
                {Object.keys(stats.character_distribution).length === 0 && (
                  <p style={{ color: '#999' }}>暂无数据</p>
                )}
              </div>
            ) : (
              <p style={{ color: '#999' }}>加载中...</p>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="活跃角色数">
            <Statistic value={activeCharacters} suffix="个角色" />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
