export interface LightningFsFile {
  type: 'file' | 'dir';
  mode: string;
  size: number;
  ino: number;
  mtimeMs: number;
  ctimeMs: number;
  // All below values are fixed to value of 1
  uid: number;
  gid: number;
  dev: number;

  isFile(): boolean;
  isDirectory(): boolean;
  isSymbolicLink(): boolean;
}
