import { useState, useEffect } from 'react';
import { Table, Tag, Select, Space, Button, Modal, message } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import api from '../services/api';

interface Memory {
  id: string;
  user_id: string;
  character_id: string;
  content: string;
  category: string;
  importance: number;
  created_at: string;
}

const CHARACTER_NAMES: Record<string, string> = {
  yinyue: '银月',
  babata: '巴巴塔',
  heihaung: '黑皇',
};

const CATEGORY_COLORS: Record<string, string> = {
  daily: 'blue',
  emotion: 'red',
  preference: 'green',
  event: 'orange',
};

export default function MemoryManagement() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(false);
  const [characterFilter, setCharacterFilter] = useState<string | undefined>();
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  useEffect(() => {
    fetchMemories();
  }, [pagination.current, pagination.pageSize, characterFilter]);

  const fetchMemories = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page: pagination.current,
        page_size: pagination.pageSize,
      };
      if (characterFilter) {
        params.character_id = characterFilter;
      }
      const response = await api.get('/admin/memories', { params });
      setMemories(response.data.items || []);
      setPagination({
        ...pagination,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error('加载记忆列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (memory: Memory) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条记忆吗？此操作不可恢复。',
      onOk: async () => {
        try {
          await api.delete(`/admin/memories/${memory.id}`);
          message.success('删除成功');
          fetchMemories();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      render: (id: string) => id.substring(0, 8) + '...',
    },
    {
      title: '角色',
      dataIndex: 'character_id',
      key: 'character_id',
      render: (c: string) => <Tag color="purple">{CHARACTER_NAMES[c] || c}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (c: string) => <Tag color={CATEGORY_COLORS[c] || 'default'}>{c}</Tag>,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '重要度',
      dataIndex: 'importance',
      key: 'importance',
      sorter: (a: Memory, b: Memory) => a.importance - b.importance,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Memory) => (
        <Space>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Select
          placeholder="角色筛选"
          style={{ width: 150 }}
          allowClear
          value={characterFilter}
          onChange={(v) => setCharacterFilter(v)}
          options={[
            { value: 'yinyue', label: '银月' },
            { value: 'babata', label: '巴巴塔' },
            { value: 'heihaung', label: '黑皇' },
          ]}
        />
      </div>
      <Table
        columns={columns}
        dataSource={memories}
        rowKey="id"
        loading={loading}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条记忆`,
          onChange: (page, pageSize) => {
            setPagination({ ...pagination, current: page, pageSize: pageSize || 20 });
          },
        }}
      />
    </div>
  );
}
