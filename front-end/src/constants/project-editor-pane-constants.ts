import { ActiveSidebarPaneToContainerMapping, SIDEBAR_PANE } from '@/types/project-editor-types';
import RunEditorCodeBlockPane from '@/components/ProjectEditor/RunEditorCodeBlockPane';
import RunDeployedCodeBlockPane from '@/components/DeploymentViewer/RunDeployedCodeBlockPane';
import AddBlockPane from '@/components/ProjectEditor/AddBlockPane';
import AddSavedBlockPaneContainer from '@/components/ProjectEditor/saved-blocks-components/AddSavedBlockPaneContainer';
import AddTransitionPane from '@/components/ProjectEditor/AddTransitionPane';
import ExportProjectPane from '@/components/ProjectEditor/ExportProjectPane';
import DeployProjectPane from '@/components/ProjectEditor/DeployProjectPane';
import EditBlockPane from '@/components/ProjectEditor/EditBlockPane';
import EditTransitionPane from '@/components/ProjectEditor/EditTransitionPane';
import ViewApiEndpointsPane from '@/components/DeploymentViewer/ViewApiEndpointsPane';
import ViewExecutionsPane from '@/components/DeploymentViewer/ViewExecutionsPane';
import DestroyDeploymentPane from '@/components/DeploymentViewer/DestroyDeploymentPane';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';
import ViewDeployedBlockLogsPane from '@/components/DeploymentViewer/ViewDeployedBlockLogsPane';
import ViewDeployedTransitionPane from '@/components/DeploymentViewer/ViewDeployedTransitionPane';
import SharedFilesPane from '@/components/ProjectEditor/SharedFiles';
import EditSharedFilePane from '@/components/ProjectEditor/EditSharedFile';
import EditSharedFileLinksPane from '@/components/ProjectEditor/SharedFileLinks';
import AddingSharedFileLinkPane from '@/components/ProjectEditor/AddingSharedFileLink';
import CodeBlockSharedFilesPane from '@/components/ProjectEditor/CodeBlockSharedFiles';
import ViewSharedFilePane from '@/components/ProjectEditor/ViewSharedFile';
import ViewReadmePane from '@/components/ProjectEditor/ViewReadme';
import EditReadmePane from '@/components/ProjectEditor/EditReadme';
import { WorkflowStateType } from '@/types/graph';
import { VueClass } from 'vue-class-component/lib/declarations';
import { Vue } from 'vue/types/vue';
import { EditLambdaBlock } from '@/components/ProjectEditor/block-components/EditLambdaBlockPane';
import { EditTopicBlock } from '@/components/ProjectEditor/block-components/EditTopicBlockPane';
import { EditScheduleTriggerBlock } from '@/components/ProjectEditor/block-components/EditScheduleTriggerBlockPane';
import { EditAPIEndpointBlock } from '@/components/ProjectEditor/block-components/EditAPIEndpointBlockPane';
import { EditAPIResponseBlock } from '@/components/ProjectEditor/block-components/EditAPIResponseBlockPane';
import { EditQueueBlock } from '@/components/ProjectEditor/block-components/EditQueuePane';
import SyncProjectRepoPane from '@/components/ProjectEditor/SyncProjectRepoPane';

export const paneToContainerMapping: ActiveSidebarPaneToContainerMapping = {
  [SIDEBAR_PANE.runEditorCodeBlock]: RunEditorCodeBlockPane,
  [SIDEBAR_PANE.runDeployedCodeBlock]: RunDeployedCodeBlockPane,
  [SIDEBAR_PANE.addBlock]: AddBlockPane,
  [SIDEBAR_PANE.addSavedBlock]: AddSavedBlockPaneContainer,
  [SIDEBAR_PANE.addTransition]: AddTransitionPane,
  [SIDEBAR_PANE.allBlocks]: AddBlockPane,
  [SIDEBAR_PANE.allVersions]: AddBlockPane,
  [SIDEBAR_PANE.exportProject]: ExportProjectPane,
  [SIDEBAR_PANE.deployProject]: DeployProjectPane,
  [SIDEBAR_PANE.syncProjectRepo]: SyncProjectRepoPane,
  [SIDEBAR_PANE.saveProject]: AddBlockPane,
  [SIDEBAR_PANE.editBlock]: EditBlockPane,
  [SIDEBAR_PANE.editTransition]: EditTransitionPane,
  [SIDEBAR_PANE.viewApiEndpoints]: ViewApiEndpointsPane,
  [SIDEBAR_PANE.viewExecutions]: ViewExecutionsPane,
  [SIDEBAR_PANE.destroyDeploy]: DestroyDeploymentPane,
  [SIDEBAR_PANE.viewDeployedBlock]: ViewDeployedBlockPane,
  [SIDEBAR_PANE.viewDeployedBlockLogs]: ViewDeployedBlockLogsPane,
  [SIDEBAR_PANE.viewDeployedTransition]: ViewDeployedTransitionPane,
  [SIDEBAR_PANE.sharedFiles]: SharedFilesPane,
  [SIDEBAR_PANE.editSharedFile]: EditSharedFilePane,
  [SIDEBAR_PANE.editSharedFileLinks]: EditSharedFileLinksPane,
  [SIDEBAR_PANE.addingSharedFileLink]: AddingSharedFileLinkPane,
  [SIDEBAR_PANE.codeBlockSharedFiles]: CodeBlockSharedFilesPane,
  [SIDEBAR_PANE.viewSharedFile]: ViewSharedFilePane,
  [SIDEBAR_PANE.viewReadme]: ViewReadmePane,
  [SIDEBAR_PANE.editReadme]: EditReadmePane
};

// This returns a function because it will allow dynamic component refreshes
export type BlockTypeToEditorComponent = { [key in WorkflowStateType]: () => VueClass<Vue> };

export const blockTypeToEditorComponentLookup: BlockTypeToEditorComponent = {
  [WorkflowStateType.LAMBDA]: () => EditLambdaBlock,
  [WorkflowStateType.SNS_TOPIC]: () => EditTopicBlock,
  [WorkflowStateType.SCHEDULE_TRIGGER]: () => EditScheduleTriggerBlock,
  [WorkflowStateType.API_ENDPOINT]: () => EditAPIEndpointBlock,
  [WorkflowStateType.API_GATEWAY]: () => EditAPIEndpointBlock,
  [WorkflowStateType.WARMER_TRIGGER]: () => EditAPIEndpointBlock,
  [WorkflowStateType.API_GATEWAY_RESPONSE]: () => EditAPIResponseBlock,
  [WorkflowStateType.SQS_QUEUE]: () => EditQueueBlock
};

export const demoModeBlacklist = [SIDEBAR_PANE.saveProject, SIDEBAR_PANE.deployProject];
