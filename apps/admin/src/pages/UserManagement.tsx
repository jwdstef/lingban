import { useState, useEffect } from 'react';
import { Table, Tag, Space, Button, Input, Modal, message, Tooltip, Avatar } from 'antd';
import { SearchOutlined, UserOutlined, EyeOutlined, StopOutlined } from '@ant-design/icons';
import api from '../services/api';

interface User {
  id: string;
  nickname: string;
  phone: string | null;
  email: string | null;
  selected_character_id: string | null;
  push_token: string | null;
  push_platform: string | null;
  emotion_profile: Record<string, unknown>;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface UserRelation {
  character_id: string;
  level: number;
  label: string;
  intimacy: number;
  consecutive_days: number;
  last_chat_at: string | null;
}

interface UserDetail extends User {
  relation: UserRelation | null;
  metrics: {
    chat_messages: number;
    memories: number;
    proactive_messages: number;
    push_deliveries: number;
  };
  push_tokens: Array<{
    id: string;
    provider: string;
    platform: string;
    token_preview: string;
    permission_status: string;
    is_active: boolean;
  }>;
}

const CHARACTER_NAMES: Record<string, string> = {
  yinyue: '银月',
  babata: '巴巴塔',
  heihaung: '黑皇',
};

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null);
  const [userRelation, setUserRelation] = useState<UserRelation | null>(null);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  useEffect(() => {
    fetchUsers();
  }, [pagination.current, pagination.pageSize, appliedSearch]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/users', {
        params: {
          page: pagination.current,
          page_size: pagination.pageSize,
          ...(appliedSearch ? { search: appliedSearch } : {}),
        },
      });
      setUsers(response.data.items || []);
      setPagination({
        ...pagination,
        total: response.data.total || 0,
      });
    } catch (error) {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setAppliedSearch(value.trim());
    setPagination({ ...pagination, current: 1 });
  };

  const handleViewDetail = async (user: User) => {
    setDetailVisible(true);
    try {
      const response = await api.get(`/admin/users/${user.id}`);
      const detail = response.data as UserDetail;
      setSelectedUser(detail);
      setUserRelation(detail.relation);
    } catch (error) {
      message.error('获取用户详情失败');
      setSelectedUser({ ...user, relation: null, metrics: {
        chat_messages: 0,
        memories: 0,
        proactive_messages: 0,
        push_deliveries: 0,
      }, push_tokens: [] });
      setUserRelation(null);
    }
  };

  const handleBan = (userId: string, banned: boolean) => {
    Modal.confirm({
      title: banned ? '确认解封' : '确认封禁',
      content: banned ? '确定要解除该用户的封禁状态吗？' : '确定要封禁该用户吗？封禁后用户将无法登录。',
      onOk: async () => {
        try {
          await api.post(`/admin/users/${userId}/${banned ? 'unban' : 'ban'}`);
          message.success(banned ? '解封成功' : '封禁成功');
          fetchUsers();
        } catch (error) {
          message.error(banned ? '解封失败' : '封禁失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '用户',
      key: 'user',
      width: 200,
      render: (_: unknown, record: User) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#8b5cf6' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.nickname}</div>
            <div style={{ fontSize: 12, color: '#999' }}>
              {record.phone || record.email || '未绑定'}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: '当前角色',
      dataIndex: 'selected_character_id',
      key: 'character',
      width: 120,
      render: (id: string | null) => id ? (
        <Tag color="purple">{CHARACTER_NAMES[id] || id}</Tag>
      ) : (
        <Tag>未选择</Tag>
      ),
    },
    {
      title: '推送平台',
      dataIndex: 'push_platform',
      key: 'push_platform',
      width: 100,
      render: (platform: string | null) => platform ? (
        <Tag color={platform === 'apns' ? 'blue' : platform === 'jpush' ? 'green' : 'orange'}>
          {platform.toUpperCase()}
        </Tag>
      ) : (
        <span style={{ color: '#999' }}>未注册</span>
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: unknown, record: User) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="封禁">
            <Button
              type="text"
              size="small"
              danger={!record.settings?.banned}
              icon={<StopOutlined />}
              onClick={() => handleBan(record.id, Boolean(record.settings?.banned))}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Input.Search
          placeholder="搜索用户昵称/手机号/邮箱"
          style={{ width: 300 }}
          prefix={<SearchOutlined />}
          allowClear
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          onSearch={handleSearch}
        />
      </div>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 个用户`,
          onChange: (page, pageSize) => {
            setPagination({ ...pagination, current: page, pageSize: pageSize || 20 });
          },
        }}
      />

      {/* 用户详情弹窗 */}
      <Modal
        title="用户详情"
        open={detailVisible}
        onCancel={() => {
          setDetailVisible(false);
          setSelectedUser(null);
          setUserRelation(null);
        }}
        footer={null}
        width={600}
      >
        {selectedUser && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
              <Avatar size={64} icon={<UserOutlined />} style={{ backgroundColor: '#8b5cf6' }} />
              <div style={{ marginLeft: 16 }}>
                <h3 style={{ margin: 0 }}>{selectedUser.nickname}</h3>
                <p style={{ color: '#999', margin: '4px 0 0' }}>
                  ID: {selectedUser.id}
                </p>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <h4>基本信息</h4>
              <p>手机: {selectedUser.phone || '未绑定'}</p>
              <p>邮箱: {selectedUser.email || '未绑定'}</p>
              <p>注册时间: {new Date(selectedUser.created_at).toLocaleString('zh-CN')}</p>
              <p>
                推送: {selectedUser.push_platform
                  ? `${selectedUser.push_platform.toUpperCase()} (${selectedUser.push_token?.substring(0, 20)}...)`
                  : '未注册'}
              </p>
              <p>状态: {selectedUser.settings?.banned ? '已封禁' : '正常'}</p>
            </div>

            <div style={{ marginBottom: 16 }}>
              <h4>运营指标</h4>
              <Space size="large">
                <span>消息 {selectedUser.metrics.chat_messages}</span>
                <span>记忆 {selectedUser.metrics.memories}</span>
                <span>关怀 {selectedUser.metrics.proactive_messages}</span>
                <span>推送 {selectedUser.metrics.push_deliveries}</span>
              </Space>
            </div>

            {userRelation && (
              <div style={{ marginBottom: 16 }}>
                <h4>关系信息</h4>
                <p>角色: {CHARACTER_NAMES[userRelation.character_id] || userRelation.character_id}</p>
                <p>等级: Lv.{userRelation.level} {userRelation.label}</p>
                <p>亲密度: {userRelation.intimacy}/1000</p>
                <p>连续互动: {userRelation.consecutive_days} 天</p>
                <p>
                  最后聊天: {userRelation.last_chat_at
                    ? new Date(userRelation.last_chat_at).toLocaleString('zh-CN')
                    : '从未聊天'}
                </p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
