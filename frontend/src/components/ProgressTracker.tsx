import { Card, Progress, Typography, Alert, Steps } from 'antd'
import { LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import type { ProgressResponse } from '../types'

const { Text } = Typography

interface ProgressTrackerProps {
  taskData: ProgressResponse
}

const stageSteps = [
  { key: 'novel_parsing', title: '小说解析' },
  { key: 'character_extraction', title: '角色提取' },
  { key: 'scene_extraction', title: '场景提取' },
  { key: 'storyboard', title: '分镜设计' },
  { key: 'image_generation', title: '图像生成' },
  { key: 'voice_synthesis', title: '语音合成' },
  { key: 'video_composition', title: '视频合成' },
]

export default function ProgressTracker({ taskData }: ProgressTrackerProps) {
  const getCurrentStep = () => {
    if (taskData.status === 'completed') return stageSteps.length
    if (taskData.status === 'failed') return -1
    if (!taskData.stage) return 0
    
    const index = stageSteps.findIndex(s => s.key === taskData.stage)
    return index >= 0 ? index : 0
  }

  const currentStep = getCurrentStep()

  return (
    <Card title="解析进度" style={{ marginBottom: 24 }}>
      {taskData.status === 'failed' && (
        <Alert
          message="解析失败"
          description={taskData.error || '未知错误'}
          type="error"
          showIcon
          icon={<CloseCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {taskData.status === 'completed' && (
        <Alert
          message="解析完成"
          description="小说解析已成功完成"
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      <Progress
        percent={taskData.progress}
        status={
          taskData.status === 'completed' ? 'success' :
          taskData.status === 'failed' ? 'exception' :
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
          status={taskData.status === 'failed' ? 'error' : 'process'}
          items={stageSteps.map((step, index) => ({
            title: step.title,
            icon: index === currentStep && taskData.status === 'processing' ? 
              <LoadingOutlined /> : undefined,
          }))}
        />
      </div>

      {taskData.message && (
        <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
          <Text type="secondary">{taskData.message}</Text>
        </div>
      )}
    </Card>
  )
}
