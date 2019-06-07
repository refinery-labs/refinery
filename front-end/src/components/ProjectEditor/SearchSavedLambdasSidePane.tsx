import Vue, { CreateElement, VNode } from "vue";
import Component from "vue-class-component";
import { GetSavedProjectRequest } from "@/types/api-types";
import { namespace } from "vuex-class";

const project = namespace("project");

@Component
export default class AddBlockPane extends Vue {
  @project.State isLoadingProject!: boolean;
  @project.Action openProject!: (projectId: GetSavedProjectRequest) => {};

  public render(h: CreateElement): VNode {
    const containerClasses = {
      "editor-pane-instance": true,
      "add-block-left-pane": true,
      "display--flex": true,
      "flex-grow--1": true
    };

    // Show a nice loading animation
    if (this.isLoadingProject) {
      return (
        <div
          class={{
            ...containerClasses,
            whirl: true,
            standard: true
          }}
        />
      );
    }

    return <div>Content Woot!</div>;
  }
}
