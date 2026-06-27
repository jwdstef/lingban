import { Card, Row, Col, Tag, Button, Progress } from 'antd';
import { EditOutlined } from '@ant-design/icons';

const characters = [
  {
    id: 'yinyue',
    name: '银月',
    source: '凡人修仙传',
    description: '傲娇毒舌，外冷内热的修仙伙伴',
    tags: ['傲娇', '毒舌', '外冷内热'],
    color: '#C0C0C0',
    users: 45,
    personality: { tsundere: 80, sharpTongued: 70, gentle: 30, active: 60, mature: 70 },
  },
  {
    id: 'babata',
    name: '巴巴塔',
    source: '吞噬星空',
    description: '沉稳睿智，亦师亦友的宇宙向导',
    tags: ['沉稳', '睿智', '亦师亦友'],
    color: '#4169E1',
    users: 32,
    personality: { tsundere: 10, sharpTongued: 20, gentle: 60, active: 40, mature: 90 },
  },
  {
    id: 'heihaung',
    name: '黑皇',
    source: '遮天',
    description: '贱萌搞笑，仗义直率的欢乐担当',
    tags: ['贱萌', '搞笑', '仗义'],
    color: '#2F2F2F',
    users: 51,
    personality: { tsundere: 20, sharpTongued: 40, gentle: 50, active: 95, mature: 20 },
  },
];

export default function CharacterManagement() {
  return (
    <Row gutter={[16, 16]}>
      {characters.map((c) => (
        <Col xs={24} lg={8} key={c.id}>
          <Card
            title={
              <span>
                <span style={{ color: c.color, fontSize: 20 }}>{c.name}</span>
                <Tag style={{ marginLeft: 8 }}>{c.source}</Tag>
              </span>
            }
            extra={<Button icon={<EditOutlined />} type="text">编辑</Button>}
          >
            <p style={{ color: '#666', marginBottom: 12 }}>{c.description}</p>
            <div style={{ marginBottom: 12 }}>
              {c.tags.map((t) => (
                <Tag key={t} color="purple">{t}</Tag>
              ))}
            </div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#999' }}>使用用户: {c.users}</span>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>性格参数</div>
              <Progress percent={c.personality.tsundere} size="small" label="傲娇" />
              <Progress percent={c.personality.sharpTongued} size="small" label="毒舌" />
              <Progress percent={c.personality.gentle} size="small" label="温柔" />
              <Progress percent={c.personality.active} size="small" label="活跃" />
              <Progress percent={c.personality.mature} size="small" label="成熟" />
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
}
