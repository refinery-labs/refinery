import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { ApiEndpointWorkflowState } from '@/types/graph';
import { HTTP_METHOD } from '@/constants/api-constants';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import { namespace } from 'vuex-class';
import { nopWrite } from '@/utils/block-utils';
import { ProductionApiEndpointWorkflowState } from '@/types/production-workflow-types';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';
import { EditBlockPaneProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

const editBlock = namespace('project/editBlockPane');

@Component
export class EditAPIEndpointBlock extends Vue implements EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: ApiEndpointWorkflowState;
  @Prop({ required: true }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) readOnly!: boolean;

  @editBlock.Mutation setHTTPMethod!: (http_method: HTTP_METHOD) => void;
  @editBlock.Mutation setHTTPPath!: (api_path: string) => void;

  @editBlock.Getter collidingApiEndpointBlocks!: ApiEndpointWorkflowState[] | null;
  @editBlock.Getter isApiEndpointPathValid!: boolean;

  public renderApiEndpointInformation() {
    // Only render for deployed blocks
    if (!this.readOnly) {
      return null;
    }

    const productionState = this.selectedNode as ProductionApiEndpointWorkflowState;

    return (
      <b-form-group description="View the link above to access your API Endpoint.">
        <label class="d-block">Endpoint URI:</label>
        <div class="text-align--center display--inline-block">
          <a href={productionState.url} target="_blank">
            {productionState.url}
          </a>
        </div>
      </b-form-group>
    );
  }

  public renderHTTPMethodInput() {
    const onChangeHTTPMethod = this.readOnly ? nopWrite : this.setHTTPMethod;

    return (
      <b-form-group id={`block-http-method-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-http-method-${this.selectedNode.id}`}>
          HTTP Method:
        </label>
        <div class="input-group with-focus">
          <b-form-select
            options={Object.values(HTTP_METHOD)}
            disabled={this.readOnly}
            value={this.selectedNode.http_method}
            on={{ change: onChangeHTTPMethod }}
          />
        </div>
        <small class="form-text text-muted">
          The HTTP method this API Endpoint will accept. Can be <code>POST</code>/<code>GET</code>/etc.
        </small>
      </b-form-group>
    );
  }

  public renderHTTPPathInput() {
    const onChangeHTTPPath = this.readOnly ? nopWrite : this.setHTTPPath;

    return (
      <b-form-group id={`block-http-path-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-http-path-${this.selectedNode.id}`}>
          HTTP Path:
        </label>
        <div class="input-group with-focus">
          <div class="input-group-prepend">
            <span class="input-group-text">/refinery</span>
          </div>
          <b-form-input
            type="text"
            required
            readonly={this.readOnly}
            value={this.selectedNode.api_path}
            on={{ input: onChangeHTTPPath }}
            placeholder="/"
          />
        </div>
        <small class="form-text text-muted">
          The path to your API Endpoint, e.g: <code>/api/v1/example</code>.
        </small>
        <b-form-invalid-feedback state={this.isApiEndpointPathValid}>
          HTTP Path must contain only letters, numbers, and forward slashes (/).
        </b-form-invalid-feedback>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#api-endpoint-block' }} />
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        {this.renderApiEndpointInformation()}
        {this.renderHTTPMethodInput()}
        {this.renderHTTPPathInput()}

        <b-form-invalid-feedback
          state={this.collidingApiEndpointBlocks && this.collidingApiEndpointBlocks.length === 0}
        >
          Error: HTTP Path and Method collision with the following blocks:
          <br />
          <ul>{this.collidingApiEndpointBlocks && this.collidingApiEndpointBlocks.map(w => <li>{w.name}</li>)}</ul>
          You must change this block's configuration before you may save changes.
        </b-form-invalid-feedback>
      </div>
    );
  }
}
