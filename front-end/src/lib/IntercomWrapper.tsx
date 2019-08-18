import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop, Watch } from 'vue-property-decorator';

@Component
export default class IntercomWrapper extends Vue {
  // @Prop({ required: true }) userId!: string | null;
  @Prop({ required: true }) name!: string | null;
  @Prop({ required: true }) email!: string | null;
  @Prop({ required: true }) intercomUserHmac!: string | null;

  @Watch('email')
  watchEmail(newEmail: string | null, oldEmail: string | null) {
    // @ts-ignore
    this.$intercom.update({ email: newEmail });

    this.mountFullStory();
  }

  @Watch('name')
  watchName(newName: string | null, oldName: string | null) {
    // @ts-ignore
    this.$intercom.update({ name: newName });

    this.mountFullStory();
  }

  @Watch('intercomUserHmac')
  watchHmac(intercomUserHmac: string | null) {
    // @ts-ignore
    this.$intercom.update({ user_hash: intercomUserHmac });

    this.mountFullStory();
  }

  mounted() {
    // @ts-ignore
    this.$intercom.boot({
      // user_id: this.userId,
      name: this.name,
      email: this.email,
      user_hash: this.intercomUserHmac,
      custom_launcher_selector: '.intercom-open-chat-button',
      hide_default_launcher: true
    });

    this.mountFullStory();
  }

  async mountFullStory() {
    // Add user data to FullStory session
    // @ts-ignore
    if (window.FS && this.email && this.name && !window.fsMounted) {
      const uniqueId = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(this.email));

      // @ts-ignore
      window.FS.identify(uniqueId, {
        displayName: this.name,
        email: this.email
      });

      // @ts-ignore
      window.fsMounted = true;
    }
  }

  render() {
    return null;
  }
}
