import { Table, Tag, Space, Button, Input } from 'antd';
import { SearchOutlined, PlusOutlined } from '@ant-design/icons';

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 100 },
  { title: '昵称', dataIndex: 'nickname', key: 'nickname' },
  { title: '手机', dataIndex: 'phone', key: 'phone' },
  {
    title: '当前角色',
    dataIndex: 'character',
    key: 'character',
    render: (c: string) => <Tag color="purple">{c}</Tag>,
  },
  {
    title: '关系等级',
    dataIndex: 'level',
    key: 'level',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (s: string) => (
      <Tag color={s === 'active' ? 'green' : 'red'}>
        {s === 'active' ? '活跃' : '封禁'}
      </Tag>
    ),
  },
  { title: '注册时间', dataIndex: 'created_at', key: 'created_at' },
  {
    title: '操作',
    key: 'action',
    render: () => (
      <Space>
        <Button type="link" size="small">详情</Button>
        <Button type="link" size="small" danger>封禁</Button>
      </Space>
    ),
  },
];

const mockData = [
  { id: '001', nickname: '小明', phone: '138****1234', character: '银月', level: 'Lv.3 熟悉', status: 'active', created_at: '2025-01-15' },
  { id: '002', nickname: '阿花', phone: '139****5678', character: '巴巴塔', level: 'Lv.2 认识', status: 'active', created_at: '2025-01-20' },
  { id: '003', nickname: '大壮', phone: '137****9012', character: '黑皇', level: 'Lv.5 挚友', status: 'active', created_at: '2025-01-10' },
];

export default function UserManagement() {
  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Input.Search
          placeholder="搜索用户昵称/手机号"
          style={{ width: 300 }}
          prefix={<SearchOutlined />}
        />
        <Button type="primary" icon={<PlusOutlined />}>添加用户</Button>
      </div>
      <Table columns={columns} dataSource={mockData} rowKey="id" />
    </div>
  );
}
