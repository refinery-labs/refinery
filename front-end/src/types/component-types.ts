import {SupportedLanguage} from '@/types/graph';

export interface EditorProps {
  id: string,
  lang: SupportedLanguage | 'text',
  content: string,
  theme?: string,
  on?: {[key: string]: Function},

  // Ace Props
  readOnly?: boolean,
  disabled?: boolean,
}
