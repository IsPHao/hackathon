import { Form, Input, Button, Card, Select } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { CreateProjectRequest } from '../types'

const { TextArea } = Input

interface NovelInputProps {
  onSubmit: (values: CreateProjectRequest) => void
  loading?: boolean
}

export default function NovelInput({ onSubmit, loading }: NovelInputProps) {
  const [form] = Form.useForm()

  const handleSubmit = (values: CreateProjectRequest) => {
    onSubmit(values)
  }

  return (
    <Card title="输入小说文本" style={{ marginBottom: 24 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item
          name="novel_text"
          label="小说内容"
          rules={[
            { required: true, message: '请输入小说内容' },
            { min: 100, message: '小说内容至少需要100个字符' },
          ]}
        >
          <TextArea
            rows={12}
            placeholder="请输入小说文本内容..."
            showCount
            maxLength={50000}
          />
        </Form.Item>

        <Form.Item
          name={['options', 'style']}
          label="动漫风格"
          initialValue="anime"
        >
          <Select>
            <Select.Option value="anime">日本动漫</Select.Option>
            <Select.Option value="cartoon">美式卡通</Select.Option>
            <Select.Option value="realistic">写实风格</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          name={['options', 'quality']}
          label="生成质量"
          initialValue="standard"
        >
          <Select>
            <Select.Option value="standard">标准</Select.Option>
            <Select.Option value="high">高质量</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            icon={<UploadOutlined />}
            loading={loading}
            size="large"
          >
            开始生成动漫
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
