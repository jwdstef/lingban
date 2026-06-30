import { useState, useEffect } from 'react';
import { Card, Row, Col, Tag, Button, Progress, Modal, Form, Input, InputNumber, message, Drawer, Divider, Space } from 'antd';
import { EditOutlined, EyeOutlined } from '@ant-design/icons';
import api from '../services/api';

interface Character {
  id: string;
  name: string;
  source: string;
  description: string;
  avatar_url: string;
  color: number;
  personality: Record<string, number>;
  system_prompt?: string;
}

export default function CharacterManagement() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(false);
  const [editVisible, setEditVisible] = useState(false);
  const [promptVisible, setPromptVisible] = useState(false);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchCharacters();
  }, []);

  const fetchCharacters = async () => {
    setLoading(true);
    try {
      const response = await api.get('/characters');
      setCharacters(response.data);
    } catch (error) {
      message.error('加载角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (character: Character) => {
    setSelectedCharacter(character);
    form.setFieldsValue({
      name: character.name,
      source: character.source,
      description: character.description,
      ...character.personality,
    });
    setEditVisible(true);
  };

  const handleViewPrompt = async (character: Character) => {
    setSelectedCharacter(character);
    try {
      // 获取角色详情（包含 system_prompt）
      const response = await api.get(`/characters/${character.id}`);
      setSelectedCharacter(response.data);
    } catch (error) {
      console.error('获取角色详情失败', error);
    }
    setPromptVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const { name, source, description, ...personality } = values;

      await api.put(`/characters/${selectedCharacter?.id}`, {
        name,
        source,
        description,
        personality,
      });

      message.success('保存成功');
      setEditVisible(false);
      fetchCharacters();
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleSavePrompt = async (prompt: string) => {
    try {
      await api.put(`/characters/${selectedCharacter?.id}`, {
        system_prompt: prompt,
      });
      message.success('Prompt 保存成功');
      setPromptVisible(false);
    } catch (error) {
      message.error('保存失败');
    }
  };

  const personalityLabels: Record<string, string> = {
    tsundere: '傲娇',
    sharp_tongued: '毒舌',
    gentle: '温柔',
    active: '活跃',
    mature: '成熟',
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        {characters.map((c) => {
          const colorHex = `#${(c.color & 0xFFFFFF).toString(16).padStart(6, '0')}`;
          const personality = c.personality || {};

          return (
            <Col xs={24} lg={8} key={c.id}>
              <Card
                loading={loading}
                title={
                  <span>
                    <span style={{ color: colorHex, fontSize: 20, fontWeight: 600 }}>{c.name}</span>
                    <Tag style={{ marginLeft: 8 }}>{c.source}</Tag>
                  </span>
                }
                extra={
                  <Space>
                    <Button
                      icon={<EyeOutlined />}
                      type="text"
                      onClick={() => handleViewPrompt(c)}
                    >
                      Prompt
                    </Button>
                    <Button
                      icon={<EditOutlined />}
                      type="text"
                      onClick={() => handleEdit(c)}
                    >
                      编辑
                    </Button>
                  </Space>
                }
              >
                <p style={{ color: '#666', marginBottom: 12 }}>{c.description}</p>

                <div style={{ marginBottom: 12 }}>
                  {Object.entries(personality).slice(0, 5).map(([key, value]) => (
                    <div key={key} style={{ marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: '#999', display: 'inline-block', width: 50 }}>
                        {personalityLabels[key] || key}
                      </span>
                      <Progress
                        percent={value as number}
                        size="small"
                        style={{ display: 'inline-block', width: 'calc(100% - 60px)' }}
                        strokeColor={colorHex}
                      />
                    </div>
                  ))}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* 编辑角色弹窗 */}
      <Modal
        title={`编辑角色 - ${selectedCharacter?.name}`}
        open={editVisible}
        onCancel={() => setEditVisible(false)}
        onOk={handleSave}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="source" label="来源" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Divider />
          <h4>性格参数</h4>
          {Object.entries(personalityLabels).map(([key, label]) => (
            <Form.Item key={key} name={key} label={label}>
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
          ))}
        </Form>
      </Modal>

      {/* Prompt 编辑抽屉 */}
      <Drawer
        title={`System Prompt - ${selectedCharacter?.name}`}
        open={promptVisible}
        onClose={() => setPromptVisible(false)}
        width={600}
        extra={
          <Button type="primary" onClick={() => {
            const prompt = (document.getElementById('prompt-editor') as HTMLTextAreaElement)?.value;
            if (prompt) handleSavePrompt(prompt);
          }}>
            保存
          </Button>
        }
      >
        <Input.TextArea
          id="prompt-editor"
          rows={30}
          defaultValue={selectedCharacter?.system_prompt || ''}
          style={{ fontFamily: 'monospace', fontSize: 13 }}
        />
      </Drawer>
    </div>
  );
}
