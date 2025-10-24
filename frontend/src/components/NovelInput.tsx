import { useState } from 'react'
import { Form, Input, Button, Card, Select, Slider, Row, Col, Collapse, Space, Typography, Upload, message as antMessage } from 'antd'
import { UploadOutlined, PictureOutlined, ThunderboltOutlined, ExperimentOutlined } from '@ant-design/icons'
import type { CreateProjectRequest } from '../types'

const { TextArea } = Input
const { Text } = Typography
const { Panel } = Collapse

interface NovelInputProps {
  onSubmit: (values: CreateProjectRequest) => void
  loading?: boolean
}

const stylePresets = [
  { value: 'anime', label: '日本动漫', description: '经典日式动画风格' },
  { value: 'cyberpunk', label: '赛博朋克', description: '未来科幻霓虹风格' },
  { value: 'moe', label: '萌系', description: '可爱治愈风格' },
  { value: 'cartoon', label: '美式卡通', description: '美国卡通风格' },
  { value: 'realistic', label: '写实风格', description: '接近真实的画风' },
  { value: 'fantasy', label: '奇幻风格', description: '魔幻奇幻风格' },
]

export default function NovelInput({ onSubmit, loading }: NovelInputProps) {
  const [form] = Form.useForm()
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSubmit = (values: CreateProjectRequest) => {
    const wordCount = values.novel_text?.length || 0
    if (wordCount < 100) {
      antMessage.warning('小说内容至少需要100个字符')
      return
    }
    onSubmit(values)
  }

  const handleUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      form.setFieldValue('novel_text', text)
      antMessage.success('文件上传成功')
    }
    reader.readAsText(file)
    return false
  }

  return (
    <Card title="创建动漫项目" style={{ marginBottom: 24 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          options: {
            style: 'anime',
            quality: 'standard',
            speed: 'normal',
            styleStrength: 75,
            colorTone: 'balanced',
            lineThickness: 50,
          }
        }}
      >
        <Form.Item
          name="novel_text"
          label={
            <Space>
              <span>小说内容</span>
              <Upload
                accept=".txt"
                showUploadList={false}
                beforeUpload={handleUpload}
              >
                <Button size="small" icon={<UploadOutlined />}>上传文本文件</Button>
              </Upload>
            </Space>
          }
          rules={[
            { required: true, message: '请输入小说内容' },
            { min: 100, message: '小说内容至少需要100个字符' },
          ]}
        >
          <TextArea
            rows={12}
            placeholder="请输入小说文本内容，或点击上方按钮上传.txt文件...\n\n支持拖拽文本直接粘贴，最多支持50000字符"
            showCount
            maxLength={50000}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Form.Item
              name={['options', 'style']}
              label="动漫风格"
              tooltip="选择预设风格模板，快速应用特定画风"
            >
              <Select
                size="large"
                options={stylePresets.map(preset => ({
                  value: preset.value,
                  label: (
                    <div>
                      <div>{preset.label}</div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{preset.description}</Text>
                    </div>
                  ),
                }))}
              />
            </Form.Item>
          </Col>

          <Col xs={24} md={12}>
            <Form.Item
              name={['options', 'quality']}
              label="生成质量"
              tooltip="高质量生成时间更长，但效果更精美"
            >
              <Select size="large">
                <Select.Option value="fast">
                  <Space>
                    <ThunderboltOutlined />
                    快速模式（较低分辨率）
                  </Space>
                </Select.Option>
                <Select.Option value="standard">标准模式（推荐）</Select.Option>
                <Select.Option value="high">
                  <Space>
                    <ExperimentOutlined />
                    高质量模式（耗时较长）
                  </Space>
                </Select.Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Collapse
          ghost
          activeKey={showAdvanced ? ['advanced'] : []}
          onChange={(keys) => setShowAdvanced(keys.includes('advanced'))}
        >
          <Panel header="高级参数设置（可选）" key="advanced">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  name={['options', 'styleStrength']}
                  label="风格强度"
                  tooltip="控制选定风格的应用强度"
                >
                  <Slider
                    marks={{ 0: '弱', 50: '中', 100: '强' }}
                    tooltipVisible
                  />
                </Form.Item>
              </Col>

              <Col xs={24} md={12}>
                <Form.Item
                  name={['options', 'lineThickness']}
                  label="线条粗细"
                  tooltip="调节画面线条的粗细程度"
                >
                  <Slider
                    marks={{ 0: '细', 50: '中', 100: '粗' }}
                    tooltipVisible
                  />
                </Form.Item>
              </Col>

              <Col xs={24} md={12}>
                <Form.Item
                  name={['options', 'colorTone']}
                  label="色彩倾向"
                >
                  <Select>
                    <Select.Option value="warm">暖色调</Select.Option>
                    <Select.Option value="balanced">平衡色调</Select.Option>
                    <Select.Option value="cool">冷色调</Select.Option>
                    <Select.Option value="vibrant">鲜艳色彩</Select.Option>
                    <Select.Option value="pastel">柔和色彩</Select.Option>
                  </Select>
                </Form.Item>
              </Col>

              <Col xs={24} md={12}>
                <Form.Item
                  name={['options', 'characterConsistency']}
                  label="角色一致性"
                  tooltip="更高的一致性可确保角色在不同场景保持相同外观"
                >
                  <Select>
                    <Select.Option value="standard">标准</Select.Option>
                    <Select.Option value="high">高（推荐）</Select.Option>
                    <Select.Option value="strict">严格</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          </Panel>
        </Collapse>

        <Form.Item style={{ marginTop: 24 }}>
          <Button
            type="primary"
            htmlType="submit"
            icon={<PictureOutlined />}
            loading={loading}
            size="large"
            block
          >
            {loading ? '正在创建项目...' : '开始生成动漫'}
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
