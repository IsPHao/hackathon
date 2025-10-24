import { Modal, Descriptions, Typography, Divider } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

interface HelpModalProps {
  visible: boolean
  onClose: () => void
}

const keyboardShortcuts = [
  { key: 'Ctrl + R', description: '重新生成当前项目' },
  { key: 'Ctrl + D', description: '下载视频' },
  { key: 'Ctrl + S', description: '保存当前项目' },
  { key: 'Ctrl + Z', description: '撤销上一步操作' },
  { key: 'Shift + /', description: '显示帮助' },
  { key: 'Esc', description: '关闭弹窗/取消操作' },
]

export default function HelpModal({ visible, onClose }: HelpModalProps) {
  return (
    <Modal
      title={
        <span>
          <QuestionCircleOutlined style={{ marginRight: 8 }} />
          使用帮助
        </span>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <Title level={4}>功能说明</Title>
      <Paragraph>
        本系统可以将小说文本自动转换为动漫视频，支持多种风格和高级参数调整。
      </Paragraph>

      <Divider />

      <Title level={4}>快捷键</Title>
      <Descriptions column={1} bordered size="small">
        {keyboardShortcuts.map(shortcut => (
          <Descriptions.Item
            key={shortcut.key}
            label={<code style={{ padding: '2px 6px', background: '#f0f0f0', borderRadius: 3 }}>{shortcut.key}</code>}
          >
            {shortcut.description}
          </Descriptions.Item>
        ))}
      </Descriptions>

      <Divider />

      <Title level={4}>注意事项</Title>
      <ul>
        <li>小说内容至少需要100个字符</li>
        <li>高质量模式生成时间较长，但效果更好</li>
        <li>生成过程中请勿关闭页面</li>
        <li>系统会自动保存最近20个项目历史</li>
        <li>所有上传内容仅用于生成动漫，不会用于其他用途</li>
      </ul>
    </Modal>
  )
}
