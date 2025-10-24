import { Select } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { useTranslation, type SupportedLocale } from '../i18n'

const languageOptions = [
  { value: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { value: 'en-US', label: 'English', flag: '🇺🇸' },
  { value: 'ja-JP', label: '日本語', flag: '🇯🇵' },
]

export default function LanguageSelector() {
  const { locale, changeLocale } = useTranslation()

  return (
    <Select
      value={locale}
      onChange={(value) => changeLocale(value as SupportedLocale)}
      style={{ width: 150 }}
      suffixIcon={<GlobalOutlined />}
      options={languageOptions.map(lang => ({
        value: lang.value,
        label: (
          <span>
            <span style={{ marginRight: 8 }}>{lang.flag}</span>
            {lang.label}
          </span>
        ),
      }))}
    />
  )
}
