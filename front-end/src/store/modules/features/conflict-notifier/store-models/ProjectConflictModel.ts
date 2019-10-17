import { Model } from '@vuex-orm/core';
import ProjectModel from '@/store/modules/features/project/store-models/ProjectModel';

export default class Post extends Model {
  static entity = 'conflict-notifier';

  // `this.belongsTo` is for the belongs to relationship.
  static fields() {
    return {
      conflictDetected: this.attr(false),
      project_id: this.belongsTo(ProjectModel, 'project_id')
    };
  }
}
