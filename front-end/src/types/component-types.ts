import {SupportedLanguage} from '@/types/graph';

export interface EditorProps {
  id: string,
  lang: SupportedLanguage | 'text',
  content: string,
  theme?: string,
  onChange?: (s: string) => void,
  onChangeContext?: (c: {value: string, this: any}) => void,

  // Ace Props
  readOnly?: boolean,
  disabled?: boolean,
  wrapText?: boolean
}
