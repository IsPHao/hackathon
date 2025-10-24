import { Card, Empty, Button, Space, message, Dropdown } from 'antd'
import { PlayCircleOutlined, DownloadOutlined, ShareAltOutlined, TwitterOutlined, FacebookOutlined, LinkOutlined } from '@ant-design/icons'
import type { MenuProps } from 'antd'
import type { Project } from '../types'

interface VideoPlayerProps {
  project: Project
}

export default function VideoPlayer({ project }: VideoPlayerProps) {
  const handleDownload = async () => {
    if (!project.video_url) return
    
    try {
      const response = await fetch(project.video_url)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `anime-${project.id}.mp4`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success('视频下载开始')
    } catch (error) {
      message.error('下载失败，请重试')
      console.error('Download failed:', error)
    }
  }

  const handleCopyLink = () => {
    const url = `${window.location.origin}/projects/${project.id}`
    navigator.clipboard.writeText(url)
      .then(() => message.success('链接已复制到剪贴板'))
      .catch(() => message.error('复制失败'))
  }

  const handleShare = (platform: string) => {
    const url = `${window.location.origin}/projects/${project.id}`
    const text = '查看我刚生成的动漫视频！'
    
    let shareUrl = ''
    switch (platform) {
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`
        break
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`
        break
      default:
        return
    }
    
    window.open(shareUrl, '_blank', 'width=600,height=400')
  }

  const shareMenuItems: MenuProps['items'] = [
    {
      key: 'copy',
      icon: <LinkOutlined />,
      label: '复制链接',
      onClick: handleCopyLink,
    },
    {
      key: 'twitter',
      icon: <TwitterOutlined />,
      label: '分享到 Twitter',
      onClick: () => handleShare('twitter'),
    },
    {
      key: 'facebook',
      icon: <FacebookOutlined />,
      label: '分享到 Facebook',
      onClick: () => handleShare('facebook'),
    },
  ]

  if (!project.video_url) {
    return (
      <Card title="视频预览">
        <Empty
          image={<PlayCircleOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
          description="视频尚未生成"
        />
      </Card>
    )
  }

  return (
    <Card 
      title="视频预览"
      extra={
        <Space>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleDownload}
          >
            高清下载
          </Button>
          <Dropdown menu={{ items: shareMenuItems }} placement="bottomRight">
            <Button icon={<ShareAltOutlined />}>
              分享
            </Button>
          </Dropdown>
        </Space>
      }
    >
      <video
        controls
        style={{ width: '100%', maxHeight: '600px', borderRadius: '8px' }}
        src={project.video_url}
        poster={project.video_url?.replace('.mp4', '-thumbnail.jpg')}
      >
        您的浏览器不支持视频播放
      </video>
    </Card>
  )
}
