export interface Project {
  id: string
  user_id: string
  novel_text: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
  updated_at: string
  video_url?: string
  current_stage?: string
}

export interface Character {
  id: string
  project_id: string
  name: string
  description: string
  reference_image_url?: string
  features: Record<string, unknown>
  created_at: string
}

export interface Scene {
  id: string
  project_id: string
  scene_number: number
  description: string
  image_url?: string
  audio_url?: string
  duration: number
  metadata: Record<string, unknown>
  created_at: string
}

export interface Video {
  id: string
  project_id: string
  video_url: string
  thumbnail_url?: string
  duration: number
  file_size: number
  created_at: string
}

export interface CreateProjectRequest {
  novel_text: string
  options?: {
    max_characters?: number
    max_scenes?: number
  }
}

export interface CreateProjectResponse {
  project_id: string
  status: string
  created_at: string
}

export interface GenerateResponse {
  task_id: string
  status: string
  estimated_time: number
}

export interface ProgressMessage {
  type: 'progress' | 'completed' | 'error'
  stage?: string
  progress?: number
  message?: string
  video_url?: string
  duration?: number
  error?: string
  details?: string
}

export interface NovelTask {
  task_id: string
  novel_text: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface NovelUploadResponse {
  task_id: string
  status: string
  created_at: string
}

export interface ParsedResult {
  characters: Character[]
  scenes: Scene[]
  video_url?: string
  metadata?: Record<string, unknown>
}

export interface ProgressState {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  stage?: string
  progress: number
  message?: string
  error?: string
}

export interface ProgressResponse extends ProgressState {
  task_id: string
  result: ParsedResult
  created_at: string
  updated_at: string
}

export interface NovelUploadRequest {
  novel_text: string
  options?: {
    max_characters?: number
    max_scenes?: number
  }
}
