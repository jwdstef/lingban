import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Input,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AlertOutlined,
  AuditOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MessageOutlined,
  ReloadOutlined,
  SearchOutlined,
  SendOutlined,
} from '@ant-design/icons';
import api from '../services/api';

const { Paragraph, Text } = Typography;

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

interface ChatAuditRecord {
  id: string;
  short_id: string;
  user_id: string;
  character_id: string;
  role: string;
  content: string;
  message_type: string;
  emotion_tags: string[];
  is_proactive: boolean;
  created_at: string;
}

interface CareRecord {
  id: string;
  short_id: string;
  user_id: string;
  character_id: string;
  trigger_type: string;
  content: string;
  delivered: boolean;
  replied: boolean;
  push_status: string;
  push_error: string | null;
  created_at: string;
}

interface PushRecord {
  id: string;
  short_id: string;
  user_id: string;
  provider: string;
  notification_type: string;
  title: string;
  body: string;
  deep_link: string | null;
  status: string;
  failure_reason: string | null;
  sent_at: string | null;
  clicked_at: string | null;
  created_at: string;
}

interface SafetyEvent {
  id: string;
  short_id: string;
  event_type: string;
  severity: string;
  user_id: string;
  character_id: string | null;
  source: string;
  source_message_id: string | null;
  content: string;
  matched_terms: string[];
  created_at: string;
  updated_at: string | null;
  status: string;
  review_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

interface AuditLog {
  id: string;
  short_id: string;
  actor_type: string;
  actor_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

type QueryParams = Record<string, string | undefined>;

const CHARACTER_NAMES: Record<string, string> = {
  yinyue: '银月',
  babata: '巴巴塔',
  heihaung: '黑皇',
};

const STATUS_LABELS: Record<string, string> = {
  pending_review: '待审核',
  in_review: '审核中',
  resolved: '已解决',
  dismissed: '已驳回',
};

const STATUS_COLORS: Record<string, string> = {
  pending_review: 'orange',
  in_review: 'blue',
  resolved: 'green',
  dismissed: 'default',
};

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-';
}

function shortId(value: string | null | undefined) {
  return value ? `${value.slice(0, 8)}...` : '-';
}

function cleanParams(params: QueryParams) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value));
}

function UserFilter({
  value,
  onChange,
  onSubmit,
  placeholder = '按用户 ID 过滤',
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
}) {
  return (
    <Space style={{ marginBottom: 16 }} wrap>
      <Input
        allowClear
        placeholder={placeholder}
        prefix={<SearchOutlined />}
        style={{ width: 320 }}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onPressEnter={onSubmit}
      />
      <Button type="primary" icon={<SearchOutlined />} onClick={onSubmit}>
        查询
      </Button>
    </Space>
  );
}

function useOperationsTable<T>(
  path: string,
  params: QueryParams = {},
): {
  data: T[];
  loading: boolean;
  pagination: { current: number; pageSize: number; total: number };
  setPagination: (pagination: { current: number; pageSize: number; total: number }) => void;
  reload: () => Promise<void>;
} {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const paramsKey = useMemo(() => JSON.stringify(params), [params]);

  const reload = async () => {
    setLoading(true);
    try {
      const response = await api.get<Paginated<T>>(path, {
        params: {
          page: pagination.current,
          page_size: pagination.pageSize,
          ...cleanParams(params),
        },
      });
      setData(response.data.items || []);
      setPagination({
        ...pagination,
        total: response.data.total || 0,
      });
    } catch {
      message.error('加载运营记录失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, paramsKey, pagination.current, pagination.pageSize]);

  return { data, loading, pagination, setPagination, reload };
}

function ChatAuditTable() {
  const [userId, setUserId] = useState('');
  const [appliedUserId, setAppliedUserId] = useState('');
  const table = useOperationsTable<ChatAuditRecord>('/admin/messages', {
    user_id: appliedUserId || undefined,
  });

  const columns: ColumnsType<ChatAuditRecord> = [
    {
      title: '消息',
      dataIndex: 'short_id',
      width: 96,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      width: 170,
      render: (id: string) => <Text copyable>{shortId(id)}</Text>,
    },
    {
      title: '角色',
      dataIndex: 'character_id',
      width: 100,
      render: (id: string) => <Tag color="purple">{CHARACTER_NAMES[id] || id}</Tag>,
    },
    {
      title: '类型',
      key: 'type',
      width: 160,
      render: (_, record) => (
        <Space size={4} wrap>
          <Tag color={record.role === 'user' ? 'blue' : 'green'}>{record.role}</Tag>
          <Tag>{record.message_type}</Tag>
          {record.is_proactive && <Tag color="gold">主动</Tag>}
        </Space>
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      ellipsis: true,
      render: (content: string) => (
        <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
          {content}
        </Paragraph>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: formatDate,
    },
  ];

  return (
    <Card>
      <UserFilter
        value={userId}
        onChange={setUserId}
        onSubmit={() => {
          table.setPagination({ ...table.pagination, current: 1 });
          setAppliedUserId(userId.trim());
        }}
      />
      <Table
        columns={columns}
        dataSource={table.data}
        loading={table.loading}
        rowKey="id"
        pagination={{
          current: table.pagination.current,
          pageSize: table.pagination.pageSize,
          total: table.pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条消息`,
          onChange: (page, pageSize) =>
            table.setPagination({
              ...table.pagination,
              current: page,
              pageSize: pageSize || 20,
            }),
        }}
      />
    </Card>
  );
}

function CareRecordsTable() {
  const [userId, setUserId] = useState('');
  const [appliedUserId, setAppliedUserId] = useState('');
  const table = useOperationsTable<CareRecord>('/admin/care/messages', {
    user_id: appliedUserId || undefined,
  });

  const columns: ColumnsType<CareRecord> = [
    {
      title: '记录',
      dataIndex: 'short_id',
      width: 96,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      width: 170,
      render: (id: string) => <Text copyable>{shortId(id)}</Text>,
    },
    {
      title: '触发',
      dataIndex: 'trigger_type',
      width: 130,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '内容',
      dataIndex: 'content',
      ellipsis: true,
    },
    {
      title: '状态',
      key: 'status',
      width: 190,
      render: (_, record) => (
        <Space size={4} wrap>
          <Tag color={record.push_status === 'sent' ? 'green' : 'default'}>
            {record.push_status}
          </Tag>
          {record.delivered && <Tag color="blue">已送达</Tag>}
          {record.replied && <Tag color="purple">已回复</Tag>}
        </Space>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: formatDate,
    },
  ];

  return (
    <Card>
      <UserFilter
        value={userId}
        onChange={setUserId}
        onSubmit={() => {
          table.setPagination({ ...table.pagination, current: 1 });
          setAppliedUserId(userId.trim());
        }}
      />
      <Table
        columns={columns}
        dataSource={table.data}
        loading={table.loading}
        rowKey="id"
        pagination={{
          current: table.pagination.current,
          pageSize: table.pagination.pageSize,
          total: table.pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条关怀记录`,
          onChange: (page, pageSize) =>
            table.setPagination({
              ...table.pagination,
              current: page,
              pageSize: pageSize || 20,
            }),
        }}
      />
    </Card>
  );
}

function PushDeliveryTable() {
  const [userId, setUserId] = useState('');
  const [appliedUserId, setAppliedUserId] = useState('');
  const table = useOperationsTable<PushRecord>('/admin/push/deliveries', {
    user_id: appliedUserId || undefined,
  });

  const columns: ColumnsType<PushRecord> = [
    {
      title: '投递',
      dataIndex: 'short_id',
      width: 96,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      width: 170,
      render: (id: string) => <Text copyable>{shortId(id)}</Text>,
    },
    {
      title: '渠道',
      dataIndex: 'provider',
      width: 100,
      render: (provider: string) => <Tag color="geekblue">{provider}</Tag>,
    },
    {
      title: '标题/内容',
      key: 'body',
      ellipsis: true,
      render: (_, record) => (
        <div>
          <Text strong>{record.title}</Text>
          <Paragraph ellipsis={{ rows: 1 }} style={{ marginBottom: 0 }}>
            {record.body}
          </Paragraph>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (status: string) => (
        <Tag color={status === 'failed' ? 'red' : status === 'clicked' ? 'purple' : 'green'}>
          {status}
        </Tag>
      ),
    },
    {
      title: '发送/点击',
      key: 'times',
      width: 220,
      render: (_, record) => (
        <div>
          <div>{formatDate(record.sent_at)}</div>
          <Text type="secondary">{formatDate(record.clicked_at)}</Text>
        </div>
      ),
    },
  ];

  return (
    <Card>
      <UserFilter
        value={userId}
        onChange={setUserId}
        onSubmit={() => {
          table.setPagination({ ...table.pagination, current: 1 });
          setAppliedUserId(userId.trim());
        }}
      />
      <Table
        columns={columns}
        dataSource={table.data}
        loading={table.loading}
        rowKey="id"
        pagination={{
          current: table.pagination.current,
          pageSize: table.pagination.pageSize,
          total: table.pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条投递记录`,
          onChange: (page, pageSize) =>
            table.setPagination({
              ...table.pagination,
              current: page,
              pageSize: pageSize || 20,
            }),
        }}
      />
    </Card>
  );
}

function SafetyEventsTable() {
  const [userId, setUserId] = useState('');
  const [appliedUserId, setAppliedUserId] = useState('');
  const [status, setStatus] = useState<string | undefined>();
  const [reviewing, setReviewing] = useState('');
  const table = useOperationsTable<SafetyEvent>('/admin/safety/events', {
    user_id: appliedUserId || undefined,
    status,
  });

  const review = async (record: SafetyEvent, nextStatus: string) => {
    setReviewing(`${record.id}:${nextStatus}`);
    try {
      await api.post(`/admin/safety/events/${record.id}/review`, {
        status: nextStatus,
        note: `管理端标记为${STATUS_LABELS[nextStatus] || nextStatus}`,
        reviewed_by: 'admin-ui',
      });
      message.success('安全事件状态已更新');
      await table.reload();
    } catch {
      message.error('更新安全事件失败');
    } finally {
      setReviewing('');
    }
  };

  const columns: ColumnsType<SafetyEvent> = [
    {
      title: '事件',
      dataIndex: 'short_id',
      width: 96,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      width: 170,
      render: (id: string) => <Text copyable>{shortId(id)}</Text>,
    },
    {
      title: '风险',
      key: 'risk',
      width: 160,
      render: (_, record) => (
        <Space size={4} wrap>
          <Tag color={record.severity === 'critical' ? 'red' : 'volcano'}>
            {record.severity}
          </Tag>
          <Tag>{record.event_type}</Tag>
        </Space>
      ),
    },
    {
      title: '内容与命中词',
      key: 'content',
      ellipsis: true,
      render: (_, record) => (
        <div>
          <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 6 }}>
            {record.content}
          </Paragraph>
          <Space size={4} wrap>
            {record.matched_terms.map((term) => (
              <Tag color="red" key={term}>
                {term}
              </Tag>
            ))}
          </Space>
        </div>
      ),
    },
    {
      title: '来源',
      key: 'source',
      width: 170,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.source}</Text>
          <Text type="secondary" copyable={!!record.source_message_id}>
            {shortId(record.source_message_id)}
          </Text>
        </Space>
      ),
    },
    {
      title: '审核',
      key: 'review',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Tag color={STATUS_COLORS[record.status] || 'default'}>
            {STATUS_LABELS[record.status] || record.status}
          </Tag>
          {record.reviewed_by && (
            <Text type="secondary">
              {record.reviewed_by} · {formatDate(record.reviewed_at)}
            </Text>
          )}
          {record.review_note && (
            <Text type="secondary" ellipsis>
              {record.review_note}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 210,
      render: (_, record) => (
        <Space size={4} wrap>
          <Tooltip title="标记为审核中">
            <Button
              size="small"
              icon={<ClockCircleOutlined />}
              disabled={record.status === 'in_review'}
              loading={reviewing === `${record.id}:in_review`}
              onClick={() => review(record, 'in_review')}
            />
          </Tooltip>
          <Tooltip title="标记为已解决">
            <Button
              size="small"
              icon={<CheckCircleOutlined />}
              disabled={record.status === 'resolved'}
              loading={reviewing === `${record.id}:resolved`}
              onClick={() => review(record, 'resolved')}
            />
          </Tooltip>
          <Tooltip title="标记为已驳回">
            <Button
              size="small"
              icon={<CloseCircleOutlined />}
              disabled={record.status === 'dismissed'}
              loading={reviewing === `${record.id}:dismissed`}
              onClick={() => review(record, 'dismissed')}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: formatDate,
    },
  ];

  return (
    <Card>
      <Space style={{ marginBottom: 16 }} wrap>
        <UserFilter
          value={userId}
          onChange={setUserId}
          onSubmit={() => {
            table.setPagination({ ...table.pagination, current: 1 });
            setAppliedUserId(userId.trim());
          }}
        />
        <Select
          allowClear
          placeholder="审核状态"
          style={{ width: 160, marginBottom: 16 }}
          value={status}
          onChange={(value) => {
            table.setPagination({ ...table.pagination, current: 1 });
            setStatus(value);
          }}
          options={[
            { label: '待审核', value: 'pending_review' },
            { label: '审核中', value: 'in_review' },
            { label: '已解决', value: 'resolved' },
            { label: '已驳回', value: 'dismissed' },
          ]}
        />
        <Button
          icon={<ReloadOutlined />}
          style={{ marginBottom: 16 }}
          onClick={() => table.reload()}
        >
          刷新
        </Button>
      </Space>
      <Table
        columns={columns}
        dataSource={table.data}
        loading={table.loading}
        rowKey="id"
        pagination={{
          current: table.pagination.current,
          pageSize: table.pagination.pageSize,
          total: table.pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条安全事件`,
          onChange: (page, pageSize) =>
            table.setPagination({
              ...table.pagination,
              current: page,
              pageSize: pageSize || 20,
            }),
        }}
      />
    </Card>
  );
}

function AuditLogsTable() {
  const [targetId, setTargetId] = useState('');
  const [appliedTargetId, setAppliedTargetId] = useState('');
  const table = useOperationsTable<AuditLog>('/admin/audit/logs', {
    target_id: appliedTargetId || undefined,
  });

  const columns: ColumnsType<AuditLog> = [
    {
      title: '日志',
      dataIndex: 'short_id',
      width: 96,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '操作者',
      key: 'actor',
      width: 160,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color={record.actor_type === 'admin' ? 'blue' : 'default'}>
            {record.actor_type}
          </Tag>
          <Text type="secondary">{record.actor_id || '-'}</Text>
        </Space>
      ),
    },
    {
      title: '动作',
      dataIndex: 'action',
      width: 190,
      render: (action: string) => <Tag color="geekblue">{action}</Tag>,
    },
    {
      title: '目标',
      key: 'target',
      width: 220,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.target_type}</Text>
          <Text type="secondary" copyable={!!record.target_id}>
            {shortId(record.target_id)}
          </Text>
        </Space>
      ),
    },
    {
      title: '元数据',
      dataIndex: 'metadata',
      ellipsis: true,
      render: (metadata: Record<string, unknown>) => (
        <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
          {JSON.stringify(metadata)}
        </Paragraph>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: formatDate,
    },
  ];

  return (
    <Card>
      <UserFilter
        value={targetId}
        onChange={setTargetId}
        placeholder="按目标 ID 过滤"
        onSubmit={() => {
          table.setPagination({ ...table.pagination, current: 1 });
          setAppliedTargetId(targetId.trim());
        }}
      />
      <Table
        columns={columns}
        dataSource={table.data}
        loading={table.loading}
        rowKey="id"
        pagination={{
          current: table.pagination.current,
          pageSize: table.pagination.pageSize,
          total: table.pagination.total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条审计日志`,
          onChange: (page, pageSize) =>
            table.setPagination({
              ...table.pagination,
              current: page,
              pageSize: pageSize || 20,
            }),
        }}
      />
    </Card>
  );
}

export default function Operations() {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Typography.Title level={4} style={{ marginBottom: 4 }}>
          运营排查
        </Typography.Title>
        <Text type="secondary">
          聚合对话抽检、主动关怀、推送投递、安全事件和审计日志，用于客服与运营定位问题。
        </Text>
      </div>
      <Tabs
        items={[
          {
            key: 'messages',
            label: (
              <Space>
                <MessageOutlined />
                对话抽检
              </Space>
            ),
            children: <ChatAuditTable />,
          },
          {
            key: 'care',
            label: (
              <Space>
                <BellOutlined />
                主动关怀
              </Space>
            ),
            children: <CareRecordsTable />,
          },
          {
            key: 'push',
            label: (
              <Space>
                <SendOutlined />
                推送投递
              </Space>
            ),
            children: <PushDeliveryTable />,
          },
          {
            key: 'safety',
            label: (
              <Space>
                <AlertOutlined />
                安全事件
              </Space>
            ),
            children: <SafetyEventsTable />,
          },
          {
            key: 'audit',
            label: (
              <Space>
                <AuditOutlined />
                审计日志
              </Space>
            ),
            children: <AuditLogsTable />,
          },
        ]}
      />
    </div>
  );
}
