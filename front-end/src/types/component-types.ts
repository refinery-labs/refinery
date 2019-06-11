import {SupportedLanguage} from '@/types/graph';

export interface EditorProps {
  id: string,
  lang: SupportedLanguage,
  content: string,
  theme?: string,
  on?: {[key: string]: Function}
}
