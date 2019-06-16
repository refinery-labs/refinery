import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { ApiEndpointWorkflowState } from '@/types/graph';
import { HTTP_METHOD } from '@/constants/api-constants';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import { namespace } from 'vuex-class';
import { nopWrite } from '@/utils/block-utils';

const editBlock = namespace('project/editBlockPane');

@Component
export class EditAPIEndpointBlock extends Vue {
  @Prop({ required: true }) selectedNode!: ApiEndpointWorkflowState;
  @Prop({ required: true }) readOnly!: boolean;

  @editBlock.Mutation setHTTPMethod!: (http_method: HTTP_METHOD) => void;
  @editBlock.Mutation setHTTPPath!: (api_path: string) => void;

  public renderHTTPMethodInput() {
    const onChangeHTTPMethod = this.readOnly ? nopWrite : this.setHTTPMethod;

    return (
      <b-form-group id={`block-http-method-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-http-method-${this.selectedNode.id}`}>
          Schedule Expression:
        </label>
        <div class="input-group with-focus">
          <b-form-select
            options={Object.values(HTTP_METHOD)}
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
            value={this.selectedNode.api_path}
            on={{ input: onChangeHTTPPath }}
            placeholder="/"
          />
        </div>
        <small class="form-text text-muted">
          The path to your API Endpoint, e.g: <code>/api/v1/example</code>.
        </small>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        {this.renderHTTPMethodInput()}
        {this.renderHTTPPathInput()}
      </div>
    );
  }
}
