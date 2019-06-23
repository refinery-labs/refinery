import Component from 'vue-class-component';
import Vue from 'vue';
import { Prop } from 'vue-property-decorator';

@Component
export class BlockDocumentationButton extends Vue {
  @Prop({ required: true }) docLink!: string;
  @Prop({ default: true }) offsetButton!: string;

  public render() {
    return (
      <div
        class="text-align--right"
        style={this.offsetButton ? 'margin-top: 10px; margin-bottom: -15px;' : 'margin-top: 10px; margin-bottom: 5px;'}
      >
        <b-button variant="outline-primary" target="_blank" href={this.docLink}>
          <span class="fas fa-book" /> Read the Docs
        </b-button>
      </div>
    );
  }
}
