import { Card, Skeleton, Space } from 'antd'

interface SkeletonLoadingProps {
  type?: 'project' | 'list' | 'video'
}

export default function SkeletonLoading({ type = 'project' }: SkeletonLoadingProps) {
  if (type === 'video') {
    return (
      <Card>
        <Skeleton.Image active style={{ width: '100%', height: 400 }} />
        <div style={{ marginTop: 16 }}>
          <Skeleton active paragraph={{ rows: 2 }} />
        </div>
      </Card>
    )
  }

  if (type === 'list') {
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {[1, 2, 3].map(i => (
          <Card key={i}>
            <Skeleton active avatar paragraph={{ rows: 3 }} />
          </Card>
        ))}
      </Space>
    )
  }

  return (
    <Card>
      <Skeleton active avatar paragraph={{ rows: 6 }} />
      <div style={{ marginTop: 24 }}>
        <Skeleton.Button active style={{ width: 200 }} />
      </div>
    </Card>
  )
}
