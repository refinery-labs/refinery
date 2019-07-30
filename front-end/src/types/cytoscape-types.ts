import { ElementsDefinition, LayoutOptions, Stylesheet } from 'cytoscape';
import { WorkflowRelationship, WorkflowState } from '@/types/graph';
import cytoscape from '@/components/CytoscapeGraph';

// Let's just not support promises in our API style. If we need it we'll figure it out
export type CyElements = ElementsDefinition;
export type CyStyle = Stylesheet[];

export interface CytoscapeGraphProps {
  elements: CyElements;
  layout: LayoutOptions | null;
  stylesheet: CyStyle;
  backgroundGrid: boolean;
  clearSelection: () => void;
  selectNode: (id: string) => void;
  selectEdge: (id: string) => void;
  selected: string | null;
  enabledNodeIds: string[] | null;
  config: cytoscape.CytoscapeOptions | null;
  windowWidth?: number;
}
