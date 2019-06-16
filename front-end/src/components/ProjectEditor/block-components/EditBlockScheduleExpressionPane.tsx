import Component from 'vue-class-component';
import Vue from 'vue';
import { ScheduleTriggerWorkflowState, WorkflowState } from '@/types/graph';
import { namespace } from 'vuex-class';
import { Prop } from 'vue-property-decorator';
import { nopWrite } from '@/utils/block-utils';

const editBlock = namespace('project/editBlockPane');

@Component
export class BlockScheduleExpressionInput extends Vue {
  @Prop({ required: true }) selectedNode!: ScheduleTriggerWorkflowState | null;

  @Prop({ required: true }) readOnly!: boolean;

  @editBlock.Mutation setScheduleExpression!: (name: string) => void;

  public render() {
    if (!this.selectedNode) {
      return null;
    }

    const selectedNode = this.selectedNode;

    const setScheduleExpression = this.readOnly ? nopWrite : this.setScheduleExpression;

    return (
      <b-form-group id={`block-schedule-expression-group-${selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-schedule-expression-${selectedNode.id}`}>
          Schedule Expression:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            id={`block-schedule-expression-${selectedNode.id}`}
            type="text"
            required
            value={selectedNode.schedule_expression}
            on={{ input: setScheduleExpression }}
            placeholder="cron(15 10 * * ? *)"
          />
        </div>
        <small class="form-text text-muted">
          <a
            href="https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html"
            target="_blank"
          >
            Schedule expression
          </a>{' '}
          indicating how often the attached blocks should be run.
        </small>
      </b-form-group>
    );
  }
}
