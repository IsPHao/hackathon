import { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { Button, message, Spin, Card, Tabs, Typography, Descriptions } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons'
import { novelApi } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import ProgressTracker from '../components/ProgressTracker'
import VideoPlayer from '../components/VideoPlayer'
import type { ProgressResponse, Character, Scene } from '../types'

const { Title } = Typography
const { TabPane } = Tabs

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [taskData, setTaskData] = useState<ProgressResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const novelText = (location.state as { novel_text?: string })?.novel_text || ''

  const handleWebSocketMessage = (data: ProgressResponse) => {
    setTaskData(data)
    
    if (data.status === 'completed') {
      message.success('小说解析完成！')
    } else if (data.status === 'failed') {
      message.error(data.error || '解析失败')
    }
  }

  const { isConnected } = useWebSocket({
    taskId: taskId || '',
    onMessage: handleWebSocketMessage,
    enabled: !!taskId && taskData?.status === 'processing',
  })

  const loadTask = async () => {
    if (!taskId) return
    
    setLoading(true)
    try {
      const data = await novelApi.getProgress(taskId)
      setTaskData(data)
    } catch (error) {
      message.error('加载任务失败')
      console.error('Failed to load task:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTask()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  const handleDownloadResult = () => {
    if (!taskData?.result) return
    
    const dataStr = JSON.stringify(taskData.result, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `task-${taskId}-result.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  if (!taskData) {
    return (
      <Card>
        <div style={{ textAlign: 'center' }}>
          <Title level={4}>任务不存在</Title>
          <Button type="primary" onClick={() => navigate('/')}>
            返回首页
          </Button>
        </div>
      </Card>
    )
  }

  const characters = taskData.result?.characters || []
  const scenes = taskData.result?.scenes || []
  const finalVideoUrl = taskData.result?.video_url && taskData.result.video_url.includes('/final_')
    ? taskData.result.video_url
    : undefined

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/')}
          style={{ marginRight: 16 }}
        >
          返回首页
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadTask}
          style={{ marginRight: 16 }}
        >
          刷新
        </Button>
        {taskData.status === 'completed' && (
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadResult}
          >
            下载结果
          </Button>
        )}
        {isConnected && (
          <span style={{ marginLeft: 16, color: '#52c41a' }}>
            实时连接已建立
          </span>
        )}
      </div>

      <Title level={3}>任务详情</Title>

      <ProgressTracker taskData={taskData} />

      {taskData.status === 'completed' && taskData.result && (
        <>
          {finalVideoUrl && (
            <VideoPlayer videoUrl={finalVideoUrl} />
          )}

          <Card title="解析结果" style={{ marginTop: 24 }}>
            <Tabs defaultActiveKey="novel">
              {novelText && (
                <TabPane tab="小说内容" key="novel">
                  <div style={{ 
                    maxHeight: '400px', 
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    padding: 16,
                    background: '#fafafa',
                    borderRadius: 4
                  }}>
                    {novelText}
                  </div>
                </TabPane>
              )}

              <TabPane tab={`角色列表 (${characters.length})`} key="characters">
                {characters.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
                    暂无角色数据
                  </div>
                ) : (
                  characters.map((character: Character, index: number) => (
                    <Card
                      key={character.id || index}
                      type="inner"
                      title={character.name}
                      style={{ marginBottom: 16 }}
                    >
                      <Descriptions column={1}>
                        <Descriptions.Item label="描述">
                          {character.description}
                        </Descriptions.Item>
                        {character.reference_image_url && (
                          <Descriptions.Item label="参考图">
                            <img 
                              src={character.reference_image_url} 
                              alt={character.name}
                              style={{ maxWidth: 200 }}
                            />
                          </Descriptions.Item>
                        )}
                      </Descriptions>
                    </Card>
                  ))
                )}
              </TabPane>

              <TabPane tab={`场景列表 (${scenes.length})`} key="scenes">
                {scenes.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
                    暂无场景数据
                  </div>
                ) : (
                  scenes.map((scene: Scene, index: number) => (
                    <Card
                      key={scene.id || index}
                      type="inner"
                      title={`场景 ${scene.scene_number}`}
                      style={{ marginBottom: 16 }}
                    >
                      <Descriptions column={1}>
                        <Descriptions.Item label="描述">
                          {scene.description}
                        </Descriptions.Item>
                        <Descriptions.Item label="时长">
                          {scene.duration}秒
                        </Descriptions.Item>
                        {scene.image_url && (
                          <Descriptions.Item label="图像">
                            <img 
                              src={scene.image_url} 
                              alt={`场景${scene.scene_number}`}
                              style={{ maxWidth: 400 }}
                            />
                          </Descriptions.Item>
                        )}
                        {scene.audio_url && (
                          <Descriptions.Item label="音频">
                            <audio controls src={scene.audio_url} />
                          </Descriptions.Item>
                        )}
                      </Descriptions>
                    </Card>
                  ))
                )}
              </TabPane>
            </Tabs>
          </Card>
        </>
      )}

      {taskData.status === 'failed' && (
        <Card style={{ marginTop: 24, textAlign: 'center' }}>
          <Title level={4}>解析失败</Title>
          <p>{taskData.error || '未知错误'}</p>
          <Button type="primary" onClick={() => navigate('/')}>
            返回首页重试
          </Button>
        </Card>
      )}
    </div>
  )
}
