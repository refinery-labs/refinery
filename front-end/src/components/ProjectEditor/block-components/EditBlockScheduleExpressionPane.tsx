import Component from 'vue-class-component';
import Vue from 'vue';
import { Prop } from 'vue-property-decorator';
import { nopWrite } from '@/utils/block-utils';
import { ScheduleExpressionInputProps } from '@/types/component-types';

@Component
export class BlockScheduleExpressionInput extends Vue implements ScheduleExpressionInputProps {
  @Prop({ required: true }) scheduleExpression!: string | null;
  @Prop({ required: true }) scheduleExpressionValid!: boolean;

  @Prop({ required: true }) readOnly!: boolean;

  @Prop({ required: true }) setScheduleExpression!: (name: string) => void;

  public render() {
    const setScheduleExpression = this.readOnly ? nopWrite : this.setScheduleExpression;

    const scheduleExpressionLink = (
      <a
        href="https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html"
        target="_blank"
      >
        Schedule expression
      </a>
    );

    return (
      <b-form-group>
        <label class="d-block">Schedule Expression:</label>
        <div class="input-group with-focus">
          <b-form-input
            type="text"
            required={true}
            value={this.scheduleExpression}
            on={{ input: setScheduleExpression }}
            placeholder="rate(2 minutes)"
          />
        </div>
        <small class="form-text text-muted">
          {scheduleExpressionLink} indicating how often the attached blocks should be run.
        </small>
        <b-form-invalid-feedback state={this.scheduleExpressionValid}>
          Value provided for the expression is invalid. Please refer to the {scheduleExpressionLink} docs for how to
          configure a valid expression.
        </b-form-invalid-feedback>
      </b-form-group>
    );
  }
}
