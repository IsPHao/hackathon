import { useState } from 'react'

export type SupportedLocale = 'zh-CN' | 'en-US' | 'ja-JP'

const translations: Record<SupportedLocale, Record<string, string>> = {
  'zh-CN': {
    'app.title': '智能动漫生成系统',
    'app.subtitle': '自动将小说文本转换为精美动漫，支持角色一致性和多模态输出',
    'novel.input': '小说内容',
    'novel.placeholder': '请输入小说文本内容...',
    'style.label': '动漫风格',
    'quality.label': '生成质量',
    'submit.button': '开始生成动漫',
    'history.title': '最近项目',
    'status.pending': '等待中',
    'status.processing': '生成中',
    'status.completed': '已完成',
    'status.failed': '失败',
  },
  'en-US': {
    'app.title': 'AI Anime Generator',
    'app.subtitle': 'Transform novels into beautiful anime with character consistency and multimodal output',
    'novel.input': 'Novel Content',
    'novel.placeholder': 'Enter your novel text...',
    'style.label': 'Anime Style',
    'quality.label': 'Generation Quality',
    'submit.button': 'Generate Anime',
    'history.title': 'Recent Projects',
    'status.pending': 'Pending',
    'status.processing': 'Processing',
    'status.completed': 'Completed',
    'status.failed': 'Failed',
  },
  'ja-JP': {
    'app.title': 'AIアニメジェネレーター',
    'app.subtitle': '小説を美しいアニメに変換、キャラクターの一貫性とマルチモーダル出力をサポート',
    'novel.input': '小説の内容',
    'novel.placeholder': '小説のテキストを入力してください...',
    'style.label': 'アニメスタイル',
    'quality.label': '生成品質',
    'submit.button': 'アニメを生成',
    'history.title': '最近のプロジェクト',
    'status.pending': '待機中',
    'status.processing': '処理中',
    'status.completed': '完了',
    'status.failed': '失敗',
  },
}

const LOCALE_STORAGE_KEY = 'app_locale'

export const getStoredLocale = (): SupportedLocale => {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored && (stored === 'zh-CN' || stored === 'en-US' || stored === 'ja-JP')) {
    return stored as SupportedLocale
  }
  
  const browserLang = navigator.language
  if (browserLang.startsWith('zh')) return 'zh-CN'
  if (browserLang.startsWith('ja')) return 'ja-JP'
  return 'en-US'
}

export const setStoredLocale = (locale: SupportedLocale) => {
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
}

export const useTranslation = () => {
  const [locale, setLocale] = useState<SupportedLocale>(getStoredLocale())

  const t = (key: string): string => {
    return translations[locale][key] || key
  }

  const changeLocale = (newLocale: SupportedLocale) => {
    setLocale(newLocale)
    setStoredLocale(newLocale)
  }

  return { t, locale, changeLocale }
}

export const getAntdLocale = (locale: SupportedLocale) => {
  switch (locale) {
    case 'zh-CN':
      return import('antd/locale/zh_CN')
    case 'en-US':
      return import('antd/locale/en_US')
    case 'ja-JP':
      return import('antd/locale/ja_JP')
    default:
      return import('antd/locale/zh_CN')
  }
}
