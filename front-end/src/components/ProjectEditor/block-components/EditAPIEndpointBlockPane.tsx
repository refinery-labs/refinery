import Component from 'vue-class-component';
import Vue, {CreateElement, VNode} from 'vue';
import {Prop} from 'vue-property-decorator';
import {ApiEndpointWorkflowState} from '@/types/graph';
import {HTTP_METHOD} from '@/constants/api-constants';
import {BlockNameInput} from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import {namespace} from 'vuex-class';

const editBlock = namespace('project/editBlockPane');

@Component
export class EditAPIEndpointBlock extends Vue {
  @Prop() selectedNode!: ApiEndpointWorkflowState;

  @editBlock.Mutation setHTTPMethod!: (http_method: HTTP_METHOD) => void;
  @editBlock.Mutation setHTTPPath!: (api_path: string) => void;

  public renderHTTPMethodInput() {
    return (
      <b-form-group id={`block-http-method-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-http-method-${this.selectedNode.id}`}>
          Schedule Expression:
        </label>
        <div class="input-group with-focus">
          <b-form-select
            options={Object.values(HTTP_METHOD)}
            value={this.selectedNode.http_method}
            on={{change: this.setHTTPMethod}}>
          </b-form-select>
        </div>
        <small class="form-text text-muted">
          The HTTP method this API Endpoint will accept. Can be <code>POST</code>/<code>GET</code>/etc.
        </small>
      </b-form-group>
    );
  };

  public renderHTTPPathInput() {
    return (
      <b-form-group id={`block-http-path-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-http-path-${this.selectedNode.id}`}>
          HTTP Path:
        </label>
        <div class="input-group with-focus">
          <div class="input-group-prepend"><span class="input-group-text">/refinery</span></div>
          <b-form-input
            type="text"
            required
            value={this.selectedNode.api_path}
            on={{input: this.setHTTPPath}}
            placeholder="/"
          />
        </div>
        <small class="form-text text-muted">
          The path to your API Endpoint, e.g: <code>/api/v1/example</code>.
        </small>
      </b-form-group>
    );
  };

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput/>
        {this.renderHTTPMethodInput()}
        {this.renderHTTPPathInput()}
      </div>
    );
  }
}