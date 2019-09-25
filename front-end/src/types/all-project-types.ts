export interface ProjectCardState {
  selectedVersion: number;
}

export type ProjectCardStateLookup = {
  [key: string]: ProjectCardState;
};

export interface SelectProjectVersion {
  projectId: string;
  selectedVersion: number;
}
