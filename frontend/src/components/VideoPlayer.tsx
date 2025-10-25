import { Card, Empty } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'

interface VideoPlayerProps {
  videoUrl?: string
}

export default function VideoPlayer({ videoUrl }: VideoPlayerProps) {
  if (!videoUrl) {
    return (
      <Card title="视频预览" style={{ marginBottom: 24 }}>
        <Empty
          image={<PlayCircleOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
          description="视频尚未生成"
        />
      </Card>
    )
  }

  return (
    <Card title="视频预览" style={{ marginBottom: 24 }}>
      <video
        controls
        style={{ width: '100%', maxHeight: '600px' }}
        src={videoUrl}
      >
        您的浏览器不支持视频播放
      </video>
    </Card>
  )
}
