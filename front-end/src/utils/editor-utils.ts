import { SupportedLanguage } from '@/types/graph';
import { languageToFileExtension } from '@/utils/project-debug-utils';

export function getLanguageFromFileExtension(fileExtension: string): SupportedLanguage {
  // This is gross, I would've thought their would be a Rambda function for this... (getting key from value in object)
  const matchingExtensions = Object.entries(languageToFileExtension).filter(
    extensionPair => fileExtension.replace('.', '') === extensionPair[1]
  );

  if (matchingExtensions.length > 0) {
    return matchingExtensions[0][0] as SupportedLanguage;
  }

  return SupportedLanguage.NODEJS_10;
}
