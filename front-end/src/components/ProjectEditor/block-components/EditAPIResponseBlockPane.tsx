import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { ApiGatewayResponseWorkflowState } from '@/types/graph';
import Component from 'vue-class-component';

@Component
export class EditAPIResponseBlock extends Vue {
  @Prop({ required: true }) selectedNode!: ApiGatewayResponseWorkflowState;

  public render(h: CreateElement): VNode {
    return (
      <div>
        <p>
          An API response is a block which will cause the data returned from the preceding linked Lambda to be sent as
          an HTTP response (encoded as JSON).
        </p>
        <p>
          Some important points to note:
          <ul>
            <li>
              The execution flow must be started by an API Endpoint Block (otherwise where would the response be
              written?).
            </li>
            <li>
              This block only returns a response the first time it is transitioned to. Future transitions are
              effectively no-operations.
            </li>
            <li>
              If it takes over 29 seconds to transition from an API Endpoint Block to an API Response Block the request
              will timeout.{' '}
              <a
                href="https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#api-gateway-execution-service-limits-table"
                target="_blank"
              >
                This is a hard limit of AWS.
              </a>
            </li>
            <li>
              An API Response Block is not tied to a particular API Endpoint Block, you can share an API Response Block
              with multiple API Endpoint Blocks.
            </li>
          </ul>
        </p>
      </div>
    );
  }
}
