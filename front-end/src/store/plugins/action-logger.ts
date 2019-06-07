import { Store } from 'vuex';
import { RootState } from '@/store/store-types';

function ActionLoggerPlugin(store: Store<RootState>) {
  store.subscribeAction((action, state) => {
    const displayAction: { type: string; payload?: any } = {
      type: action.type
    };

    if (action.payload) {
      displayAction.payload = action.payload;
    }

    console.log(`[Action Dispatch] ${action.type} \n`, displayAction);
  });
}

export default ActionLoggerPlugin;
