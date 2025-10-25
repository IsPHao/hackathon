import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Routes, Route } from 'react-router-dom'
import MainLayout from './components/MainLayout'
import HomePage from './pages/HomePage'
import TaskDetailPage from './pages/TaskDetailPage'

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<HomePage />} />
          <Route path="projects/:projectId" element={<TaskDetailPage />} />
          <Route path="tasks/:taskId" element={<TaskDetailPage />} />
        </Route>
      </Routes>
    </ConfigProvider>
  )
}

export default App
