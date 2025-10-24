import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { message, Row, Col, Card, Typography, Divider } from 'antd'
import { RocketOutlined, SafetyOutlined, ThunderboltOutlined } from '@ant-design/icons'
import NovelInput from '../components/NovelInput'
import { projectApi } from '../api/client'
import type { CreateProjectRequest } from '../types'

const { Title, Paragraph } = Typography

export default function HomePage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (values: CreateProjectRequest) => {
    setLoading(true)
    try {
      const response = await projectApi.createProject(values)
      message.success('项目创建成功，开始生成动漫...')
      
      await projectApi.generateVideo(response.project_id)
      
      navigate(`/projects/${response.project_id}`)
    } catch (error) {
      message.error('创建项目失败，请重试')
      console.error('Failed to create project:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <Title level={2}>智能动漫生成系统</Title>
        <Paragraph type="secondary" style={{ fontSize: 16 }}>
          自动将小说文本转换为精美动漫，支持角色一致性和多模态输出
        </Paragraph>
      </div>

      <Row gutter={[24, 24]} style={{ marginBottom: 48 }}>
        <Col xs={24} md={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <RocketOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
              <Title level={4}>快速生成</Title>
              <Paragraph type="secondary">
                基于先进的AI技术，快速将小说内容转换为动漫视频
              </Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <SafetyOutlined style={{ fontSize: 48, color: '#52c41a', marginBottom: 16 }} />
              <Title level={4}>角色一致</Title>
              <Paragraph type="secondary">
                智能保持角色在整个动漫中的视觉一致性
              </Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <ThunderboltOutlined style={{ fontSize: 48, color: '#faad14', marginBottom: 16 }} />
              <Title level={4}>多模态输出</Title>
              <Paragraph type="secondary">
                支持图像、文本和语音的完美结合
              </Paragraph>
            </div>
          </Card>
        </Col>
      </Row>

      <Divider />

      <NovelInput onSubmit={handleSubmit} loading={loading} />
    </div>
  )
}
