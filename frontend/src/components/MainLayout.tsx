import { Layout, Menu, Space } from 'antd'
import { HomeOutlined } from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import LanguageSelector from './LanguageSelector'

const { Header, Content, Footer } = Layout

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Space size="large">
          <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
            智能动漫生成系统
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ minWidth: 200 }}
          />
        </Space>
        <LanguageSelector />
      </Header>
      <Content style={{ padding: '24px 50px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
        <Outlet />
      </Content>
      <Footer style={{ textAlign: 'center', background: '#f0f2f5' }}>
        <Space direction="vertical" size="small">
          <div>智能动漫生成系统 ©2024</div>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>
            Powered by AI | 支持多语言 | 保护您的隐私
          </div>
        </Space>
      </Footer>
    </Layout>
  )
}
