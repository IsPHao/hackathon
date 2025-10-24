import { Card, Progress, Typography, Alert, Steps } from 'antd'
import { LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import type { Project, ProgressMessage } from '../types'

const { Text, Title } = Typography

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

export default function ProgressTracker({ project, lastMessage }: ProgressTrackerProps) {
  const getCurrentStep = () => {
    if (project.status === 'completed') return stageSteps.length
    if (project.status === 'failed') return -1
    if (!project.current_stage) return 0
    
    const index = stageSteps.findIndex(s => s.key === project.current_stage)
    return index >= 0 ? index : 0
  }

  const currentStep = getCurrentStep()

  return (
    <Card title="生成进度" style={{ marginBottom: 24 }}>
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
