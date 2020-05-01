export interface MonacoEditorProps {
  readOnly?: boolean;
  original?: string;
  value: string;
  theme?: string;
  options?: {};
  language?: string;
  diffEditor?: boolean;
  wordWrap?: boolean;
  automaticLayout?: boolean;
  tailOutput?: boolean;
  lineNumbers: boolean;

  onChange?: (s: string) => void;
}
