import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop, Watch } from 'vue-property-decorator';

@Component
export default class IntercomWrapper extends Vue {
  // @Prop({ required: true }) userId!: string | null;
  @Prop({ required: true }) name!: string | null;
  @Prop({ required: true }) email!: string | null;

  @Watch('email')
  watchEmail(newEmail: string | null, oldEmail: string | null) {
    // @ts-ignore
    this.$intercom.update({ email: newEmail });
  }

  @Watch('name')
  watchName(newName: string | null, oldName: string | null) {
    // @ts-ignore
    this.$intercom.update({ name: newName });
  }

  mounted() {
    // @ts-ignore
    this.$intercom.boot({
      // user_id: this.userId,
      name: this.name,
      email: this.email
    });
  }

  render() {
    return null;
  }
}
