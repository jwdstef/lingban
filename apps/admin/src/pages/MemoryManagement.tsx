import { Table, Tag, Select, Space, Button } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '用户', dataIndex: 'user', key: 'user' },
  { title: '角色', dataIndex: 'character', key: 'character', render: (c: string) => <Tag color="purple">{c}</Tag> },
  {
    title: '分类',
    dataIndex: 'category',
    key: 'category',
    render: (c: string) => {
      const colors: Record<string, string> = {
        daily: 'blue', emotion: 'red', preference: 'green', event: 'orange',
      };
      return <Tag color={colors[c] || 'default'}>{c}</Tag>;
    },
  },
  { title: '内容', dataIndex: 'content', key: 'content', ellipsis: true },
  { title: '重要度', dataIndex: 'importance', key: 'importance', sorter: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  {
    title: '操作',
    key: 'action',
    render: () => (
      <Space>
        <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
      </Space>
    ),
  },
];

const mockData = [
  { id: '001', user: '小明', character: '银月', category: 'daily', content: '用户今天加班到很晚，看起来很疲惫', importance: 6, created_at: '2025-01-25 22:30' },
  { id: '002', user: '小明', character: '银月', category: 'emotion', content: '用户因为项目进度感到焦虑', importance: 8, created_at: '2025-01-25 20:15' },
  { id: '003', user: '阿花', character: '巴巴塔', category: 'preference', content: '用户喜欢深夜聊天，通常在22点后活跃', importance: 5, created_at: '2025-01-24' },
];

export default function MemoryManagement() {
  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Select placeholder="角色" style={{ width: 120 }} options={[
          { value: 'yinyue', label: '银月' },
          { value: 'babata', label: '巴巴塔' },
          { value: 'heihaung', label: '黑皇' },
        ]} />
        <Select placeholder="分类" style={{ width: 120 }} options={[
          { value: 'daily', label: '日常' },
          { value: 'emotion', label: '情绪' },
          { value: 'preference', label: '偏好' },
          { value: 'event', label: '事件' },
        ]} />
      </div>
      <Table columns={columns} dataSource={mockData} rowKey="id" />
    </div>
  );
}
