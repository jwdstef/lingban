import { Card, Form, Input, Button, Switch, Select, Divider, message } from 'antd';

export default function SystemConfig() {
  const [form] = Form.useForm();

  const handleSave = () => {
    message.success('配置已保存');
  };

  return (
    <div style={{ maxWidth: 800 }}>
      <Card title="AI 模型配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Form.Item label="主力模型" name="model">
            <Select defaultValue="claude">
              <Select.Option value="claude">Claude (Anthropic)</Select.Option>
              <Select.Option value="gpt4o">GPT-4o (OpenAI)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="Anthropic API Key" name="anthropic_key">
            <Input.Password placeholder="sk-ant-..." />
          </Form.Item>
          <Form.Item label="降级模型" name="fallback_model">
            <Select defaultValue="gpt4o">
              <Select.Option value="gpt4o">GPT-4o</Select.Option>
              <Select.Option value="none">不降级</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>

      <Card title="主动关怀配置" style={{ marginBottom: 16 }}>
        <Form layout="vertical">
          <Form.Item label="启用主动关怀">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item label="主动性强度">
            <Select defaultValue="medium">
              <Select.Option value="low">低 - 每天最多1次</Select.Option>
              <Select.Option value="medium">中 - 每天最多3次</Select.Option>
              <Select.Option value="high">高 - 每天最多5次</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="免打扰时段">
            <Input defaultValue="23:00 - 08:00" />
          </Form.Item>
        </Form>
      </Card>

      <Card title="推送配置" style={{ marginBottom: 16 }}>
        <Form layout="vertical">
          <Form.Item label="推送服务">
            <Select defaultValue="jpush">
              <Select.Option value="jpush">极光推送</Select.Option>
              <Select.Option value="firebase">Firebase</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="API Key">
            <Input.Password placeholder="推送服务 API Key" />
          </Form.Item>
        </Form>
      </Card>

      <Button type="primary" onClick={handleSave} size="large">保存配置</Button>
    </div>
  );
}
