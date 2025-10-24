import { useState, useEffect } from 'react'
import { Card, List, Tag, Button, Space, Empty, Tooltip } from 'antd'
import { ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { Project } from '../types'

interface ProjectHistoryProps {
  projects?: Project[]
  loading?: boolean
  onRefresh?: () => void
}

export default function ProjectHistory({ projects = [], loading = false, onRefresh }: ProjectHistoryProps) {
  const navigate = useNavigate()
  const [localProjects, setLocalProjects] = useState<Project[]>([])

  useEffect(() => {
    const savedProjects = localStorage.getItem('project_history')
    if (savedProjects) {
      try {
        const parsed = JSON.parse(savedProjects)
        setLocalProjects(parsed)
      } catch (e) {
        console.error('Failed to parse project history:', e)
      }
    }
  }, [])

  const allProjects = [...projects, ...localProjects]
    .filter((proj, index, self) => 
      index === self.findIndex(p => p.id === proj.id)
    )
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 10)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
      case 'processing':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
    }
  }

  const getStatusText = (status: string) => {
    const statusMap: Record<string, { text: string; color: string }> = {
      pending: { text: '等待中', color: 'default' },
      processing: { text: '生成中', color: 'processing' },
      completed: { text: '已完成', color: 'success' },
      failed: { text: '失败', color: 'error' },
    }
    return statusMap[status] || statusMap.pending
  }

  const handleView = (projectId: string) => {
    navigate(`/projects/${projectId}`)
  }

  const handleDelete = (projectId: string) => {
    const updated = localProjects.filter(p => p.id !== projectId)
    setLocalProjects(updated)
    localStorage.setItem('project_history', JSON.stringify(updated))
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN')
  }

  if (allProjects.length === 0) {
    return (
      <Card title="历史记录">
        <Empty 
          description="暂无历史记录"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    )
  }

  return (
    <Card 
      title="最近项目" 
      extra={
        onRefresh && (
          <Button type="link" onClick={onRefresh}>
            刷新
          </Button>
        )
      }
    >
      <List
        loading={loading}
        dataSource={allProjects}
        renderItem={(project) => {
          const status = getStatusText(project.status)
          return (
            <List.Item
              actions={[
                <Tooltip title="查看详情" key="view">
                  <Button
                    type="link"
                    icon={<EyeOutlined />}
                    onClick={() => handleView(project.id)}
                  >
                    查看
                  </Button>
                </Tooltip>,
                <Tooltip title="从历史中移除" key="delete">
                  <Button
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(project.id)}
                  />
                </Tooltip>,
              ]}
            >
              <List.Item.Meta
                avatar={getStatusIcon(project.status)}
                title={
                  <Space>
                    <span style={{ 
                      maxWidth: 300, 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'inline-block'
                    }}>
                      {project.novel_text?.substring(0, 30)}...
                    </span>
                    <Tag color={status.color}>{status.text}</Tag>
                  </Space>
                }
                description={
                  <Space>
                    <span>{formatDate(project.created_at)}</span>
                    {project.progress > 0 && project.status === 'processing' && (
                      <Tag color="blue">{project.progress}%</Tag>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )
        }}
      />
    </Card>
  )
}
