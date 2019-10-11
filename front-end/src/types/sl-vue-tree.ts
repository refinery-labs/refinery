export interface ISlTreeNodeModel {
  title: string;
  isLeaf?: boolean;
  children?: ISlTreeNodeModel[];
  isExpanded?: boolean;
  isSelected?: boolean;
  isDraggable?: boolean;
  isSelectable?: boolean;
  data?: any;
}
export interface ISlTreeNode extends ISlTreeNodeModel {
  isVisible?: boolean;
  isFirstChild: boolean;
  isLastChild: boolean;
  ind: number;
  level: number;
  path: number[];
  pathStr: string;
  children: ISlTreeNode[];
}
export interface ICursorPosition {
  node: ISlTreeNode;
  placement: 'before' | 'inside' | 'after';
}
export interface IVueData {
  rootCursorPosition: ICursorPosition;
  rootDraggingNode: ISlTreeNode;
}
