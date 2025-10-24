import { useEffect, useState } from 'react'
import { Card, Progress, Typography, Alert, Steps, Space, Tag, Statistic } from 'antd'
import { LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import type { Project, ProgressMessage } from '../types'

const { Text } = Typography

interface ProgressTrackerProps {
  project: Project
  lastMessage?: ProgressMessage | null
}

const stageSteps = [
  { key: 'novel_parsing', title: '小说解析' },
  { key: 'storyboard', title: '分镜设计' },
  { key: 'character_consistency', title: '角色一致性' },
  { key: 'image_generation', title: '图像生成' },
  { key: 'voice_synthesis', title: '语音合成' },
  { key: 'video_composition', title: '视频合成' },
]

const estimatedTimesPerStage = {
  novel_parsing: 30,
  storyboard: 60,
  character_consistency: 90,
  image_generation: 180,
  voice_synthesis: 120,
  video_composition: 150,
}

export default function ProgressTracker({ project, lastMessage }: ProgressTrackerProps) {
  const [startTime] = useState(Date.now())
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    if (project.status === 'processing') {
      const timer = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000))
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [project.status, startTime])

  const getCurrentStep = () => {
    if (project.status === 'completed') return stageSteps.length
    if (project.status === 'failed') return -1
    if (!project.current_stage) return 0
    
    const index = stageSteps.findIndex(s => s.key === project.current_stage)
    return index >= 0 ? index : 0
  }

  const getEstimatedRemaining = () => {
    const currentStep = getCurrentStep()
    if (currentStep < 0 || currentStep >= stageSteps.length) return 0
    
    let remaining = 0
    for (let i = currentStep; i < stageSteps.length; i++) {
      const key = stageSteps[i].key as keyof typeof estimatedTimesPerStage
      remaining += estimatedTimesPerStage[key]
    }
    return remaining
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const currentStep = getCurrentStep()
  const estimatedRemaining = getEstimatedRemaining()

  return (
    <Card 
      title={
        <Space>
          <span>生成进度</span>
          {project.status === 'processing' && (
            <Tag icon={<LoadingOutlined />} color="processing">
              生成中
            </Tag>
          )}
        </Space>
      }
      extra={
        project.status === 'processing' && (
          <Space size="large">
            <Statistic
              title="已经过"
              value={formatTime(elapsedTime)}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ fontSize: 16 }}
            />
            <Statistic
              title="预计剩余"
              value={formatTime(estimatedRemaining)}
              valueStyle={{ fontSize: 16 }}
            />
          </Space>
        )
      }
      style={{ marginBottom: 24 }}
    >
      {project.status === 'failed' && (
        <Alert
          message="生成失败"
          description={lastMessage?.error || '未知错误'}
          type="error"
          showIcon
          icon={<CloseCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {project.status === 'completed' && (
        <Alert
          message="生成完成"
          description="动漫视频已成功生成"
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      <Progress
        percent={project.progress}
        status={
          project.status === 'completed' ? 'success' :
          project.status === 'failed' ? 'exception' :
          'active'
        }
        strokeColor={{
          from: '#108ee9',
          to: '#87d068',
        }}
      />

      <div style={{ marginTop: 24 }}>
        <Steps
          current={currentStep}
          status={project.status === 'failed' ? 'error' : 'process'}
          items={stageSteps.map((step, index) => ({
            title: step.title,
            icon: index === currentStep && project.status === 'processing' ? 
              <LoadingOutlined /> : undefined,
          }))}
        />
      </div>

      {lastMessage?.message && (
        <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
          <Text type="secondary">{lastMessage.message}</Text>
        </div>
      )}
    </Card>
  )
}
