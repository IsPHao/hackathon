import axios from 'axios'
import type {
  Project,
  CreateProjectRequest,
  CreateProjectResponse,
  GenerateResponse,
  Video,
  Character,
  Scene
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const projectApi = {
  createProject: async (data: CreateProjectRequest): Promise<CreateProjectResponse> => {
    const response = await apiClient.post<CreateProjectResponse>('/projects', data)
    return response.data
  },

  getProject: async (projectId: string): Promise<Project> => {
    const response = await apiClient.get<Project>(`/projects/${projectId}`)
    return response.data
  },

  generateVideo: async (projectId: string): Promise<GenerateResponse> => {
    const response = await apiClient.post<GenerateResponse>(`/projects/${projectId}/generate`)
    return response.data
  },

  listProjects: async (): Promise<Project[]> => {
    const response = await apiClient.get<Project[]>('/projects')
    return response.data
  },
}

export const videoApi = {
  getVideo: async (videoId: string): Promise<Video> => {
    const response = await apiClient.get<Video>(`/videos/${videoId}`)
    return response.data
  },
}

export const characterApi = {
  getCharacters: async (projectId: string): Promise<Character[]> => {
    const response = await apiClient.get<Character[]>(`/projects/${projectId}/characters`)
    return response.data
  },
}

export const sceneApi = {
  getScenes: async (projectId: string): Promise<Scene[]> => {
    const response = await apiClient.get<Scene[]>(`/projects/${projectId}/scenes`)
    return response.data
  },
}

export default apiClient
