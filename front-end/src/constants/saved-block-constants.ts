import { SavedBlockSaveType } from '@/types/api-types';

export type SavedBlockSaveTypeToBlockTitle = { [key in SavedBlockSaveType]: string };

export const savedBlockTitles: SavedBlockSaveTypeToBlockTitle = {
  [SavedBlockSaveType.UPDATE]: 'Update Saved Block Version',
  [SavedBlockSaveType.CREATE]: 'Create New Saved Block',
  [SavedBlockSaveType.FORK]: 'Fork Saved Block Version'
};

export const alreadyPublishedText =
  'This option is disabled. You cannot make a published block private again. If you have done this accidentally and need this block unpublished, please contact support';
export const newPublishText =
  'This will make the Saved Block, the example input, and the documentation available for other people to use. Only publish blocks that you are okay with other people seeing! You cannot remove a public block without contacting support.';

export const inputDataExample = `{
  "what": "This is some example data that your block requires",
  "who": "Use this to help users of your block get started",
  "why": "To explain what input your block expects"
}`;
