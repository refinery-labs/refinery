import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowState } from '@/types/graph';
import { ProductionApiEndpointWorkflowState } from '@/types/production-workflow-types';
import { HTTP_METHOD } from '@/constants/api-constants';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';

const deployment = namespace('deployment');

@Component
export default class ViewApiEndpointsPane extends Vue {
  @deployment.Getter getDeployedAPIEndpoints!: ProductionApiEndpointWorkflowState[];
  @deployment.Getter getSelectedBlock!: WorkflowState | null;
  @deployment.Action selectNode!: (nodeId: string) => void;

  renderAPIEndpoint(endpoint: ProductionApiEndpointWorkflowState) {
    const isActive = this.getSelectedBlock && this.getSelectedBlock.id === endpoint.id;
    const endpointPath =
      endpoint.http_method === HTTP_METHOD.GET ? (
        <a href={endpoint.url} class={isActive ? 'text-light' : ''} target="_blank">
          {endpoint.api_path}
        </a>
      ) : (
        endpoint.api_path
      );
    return (
      <b-list-group-item
        button={true}
        active={isActive}
        class="d-flex justify-content-between align-items-center"
        on={{ click: () => this.selectNode(endpoint.id) }}
      >
        <label style="margin-bottom: 0px">
          {endpoint.http_method} {endpointPath}
        </label>
      </b-list-group-item>
    );
  }

  getExampleCurlRequest(endpoint: ProductionApiEndpointWorkflowState) {
    switch (endpoint.http_method) {
      case HTTP_METHOD.GET:
        return `curl '${endpoint.url}?key=value'`;
      default:
        return `curl -X ${endpoint.http_method} -H 'Content-Type: application/json' -d '{"key":"value"}' '${
          endpoint.url
        }'`;
    }
  }

  endpointCurlRequest() {
    if (this.getSelectedBlock) {
      const selectedBlock = this.getSelectedBlock;
      const selectedEndpoints = this.getDeployedAPIEndpoints.filter(e => e.id === selectedBlock.id);
      if (selectedEndpoints.length === 1) {
        const selectedEndpoint = selectedEndpoints[0];
        return this.getExampleCurlRequest(selectedEndpoint);
      }
    }
    return 'No endpoint selected';
  }

  public render(h: CreateElement): VNode {
    if (this.getDeployedAPIEndpoints.length === 0) {
      return (
        <div class="padding--normal">
          <p>No deployed API Endpoints</p>
        </div>
      );
    }

    const editorProps: EditorProps = {
      name: `endpoint-curl-request`,
      lang: 'shell',
      readOnly: true,
      content: this.endpointCurlRequest(),
      disableFullscreen: true,
      wrapText: true,
      lineNumbers: false
    };

    return (
      <div class="min-width--500px">
        <h4 class="margin--normal">Deployed API Endpoints</h4>
        <b-list-group class="view-api-endpoints-pane-container margin--normal">
          {this.getDeployedAPIEndpoints.map(e => this.renderAPIEndpoint(e))}
        </b-list-group>
        <div class="text-align--left margin--normal">
          <p class="padding-top--normal padding-left--normal">Example endpoint curl request:</p>
          <RefineryCodeEditor props={editorProps} />
        </div>
      </div>
    );
  }
}
