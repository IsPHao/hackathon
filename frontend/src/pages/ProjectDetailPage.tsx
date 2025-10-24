import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, message, Card, Tabs, Typography, Descriptions, Space, Tag } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, SafetyCertificateOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { projectApi, characterApi, sceneApi } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut'
import ProgressTracker from '../components/ProgressTracker'
import VideoPlayer from '../components/VideoPlayer'
import SkeletonLoading from '../components/SkeletonLoading'
import HelpModal from '../components/HelpModal'
import type { Project, Character, Scene, ProgressMessage } from '../types'

const { Title } = Typography
const { TabPane } = Tabs

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [characters, setCharacters] = useState<Character[]>([])
  const [scenes, setScenes] = useState<Scene[]>([])
  const [loading, setLoading] = useState(true)
  const [helpVisible, setHelpVisible] = useState(false)

  useKeyboardShortcut([
    {
      key: 'r',
      ctrl: true,
      callback: () => {
        if (project?.status === 'failed') {
          message.info('即将支持重新生成功能')
        }
      },
    },
    {
      key: '/',
      shift: true,
      callback: () => setHelpVisible(true),
    },
  ])

  const handleWebSocketMessage = (msg: ProgressMessage) => {
    if (msg.type === 'progress' && project) {
      setProject({
        ...project,
        progress: msg.progress || project.progress,
        current_stage: msg.stage || project.current_stage,
      })
    } else if (msg.type === 'completed' && project) {
      setProject({
        ...project,
        status: 'completed',
        progress: 100,
        video_url: msg.video_url,
      })
      message.success('动漫生成完成！')
    } else if (msg.type === 'error' && project) {
      setProject({
        ...project,
        status: 'failed',
      })
      message.error('动漫生成失败')
    }
  }

  const { isConnected, lastMessage } = useWebSocket({
    projectId: projectId || '',
    onMessage: handleWebSocketMessage,
    enabled: !!projectId && project?.status === 'processing',
  })

  const loadProject = async () => {
    if (!projectId) return
    
    setLoading(true)
    try {
      const data = await projectApi.getProject(projectId)
      setProject(data)
    } catch (error) {
      message.error('加载项目失败')
      console.error('Failed to load project:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadCharacters = async () => {
    if (!projectId) return
    
    try {
      const data = await characterApi.getCharacters(projectId)
      setCharacters(data)
    } catch (error) {
      console.error('Failed to load characters:', error)
    }
  }

  const loadScenes = async () => {
    if (!projectId) return
    
    try {
      const data = await sceneApi.getScenes(projectId)
      setScenes(data)
    } catch (error) {
      console.error('Failed to load scenes:', error)
    }
  }

  useEffect(() => {
    loadProject()
  }, [projectId])

  useEffect(() => {
    if (project?.status === 'completed') {
      loadCharacters()
      loadScenes()
    }
  }, [project?.status])

  if (loading) {
    return <SkeletonLoading type="project" />
  }

  if (!project) {
    return (
      <Card>
        <div style={{ textAlign: 'center' }}>
          <Title level={4}>项目不存在</Title>
          <Button type="primary" onClick={() => navigate('/')}>
            返回首页
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <Space size="middle" wrap>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/')}
          >
            返回首页
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadProject}
          >
            刷新
          </Button>
          <Button
            icon={<QuestionCircleOutlined />}
            onClick={() => setHelpVisible(true)}
          >
            帮助
          </Button>
          {isConnected && (
            <Tag color="success" icon={<SafetyCertificateOutlined />}>
              实时连接已建立
            </Tag>
          )}
          <Tag color="blue">项目 ID: {projectId}</Tag>
        </Space>
      </Card>

      <HelpModal visible={helpVisible} onClose={() => setHelpVisible(false)} />

      <ProgressTracker project={project} lastMessage={lastMessage} />

      {project.status === 'completed' && (
        <>
          <VideoPlayer project={project} />

          <Card title="项目信息" style={{ marginTop: 24 }}>
            <Tabs defaultActiveKey="novel">
              <TabPane tab="小说内容" key="novel">
                <div style={{ 
                  maxHeight: '400px', 
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  padding: 16,
                  background: '#fafafa',
                  borderRadius: 4
                }}>
                  {project.novel_text}
                </div>
              </TabPane>

              <TabPane tab={`角色列表 (${characters.length})`} key="characters">
                {characters.map(character => (
                  <Card
                    key={character.id}
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
                ))}
              </TabPane>

              <TabPane tab={`场景列表 (${scenes.length})`} key="scenes">
                {scenes.map(scene => (
                  <Card
                    key={scene.id}
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
                ))}
              </TabPane>
            </Tabs>
          </Card>
        </>
      )}
    </div>
  )
}
