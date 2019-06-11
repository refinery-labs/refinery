import {Module} from 'vuex';
import {RootState} from '../store-types';
import {makeApiRequest} from "@/store/fetchers/refinery-api";
import {
  DeletePaymentMethodRequest,
  DeletePaymentMethodResponse,
  GetPaymentMethodsRequest,
  GetPaymentMethodsResponse
} from "@/types/api-types";
import {API_ENDPOINT} from "@/constants/api-constants";

// Enums
export enum BillingMutators {
  setPaymentMethods = 'setPaymentMethods',
  setIsLoading = 'setIsLoading',
  setRegistrationStripeTokenValue = 'setRegistrationStripeTokenValue'
}

export enum BillingActions {
  getPaymentMethods = 'getPaymentMethods',
  deletePaymentMethod = 'deletePaymentMethod',
  makePrimaryPaymentMethod = 'makePrimaryPaymentMethod'
}

// Types
export interface BillingPaneState {
  paymentMethods: PaymentMethodData[],
  isLoading: boolean,
  stripeCardToken: string | null,
}

// Initial State
const moduleState: BillingPaneState = {
  paymentMethods: [],
  isLoading: true,
  stripeCardToken: null,
};

const BillingPaneModule: Module<BillingPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [BillingMutators.setPaymentMethods](state, results: PaymentMethodData[]) {
      state.paymentMethods = results;
    },
    [BillingMutators.setIsLoading](state, isLoading: boolean) {
      state.isLoading = isLoading;
    },
    [BillingMutators.setRegistrationStripeTokenValue](state, stripeCardToken: string) {
      console.log( "STRIPE TOKEN: " );
      console.log( stripeCardToken );
      state.stripeCardToken = stripeCardToken;
    },
  },
  actions: {
    async [BillingActions.getPaymentMethods](context) {
      context.commit(BillingMutators.setIsLoading, true);
      const result = await makeApiRequest<GetPaymentMethodsRequest, GetPaymentMethodsResponse>(
        API_ENDPOINT.GetPaymentMethods,
        {}
      );
      context.commit(BillingMutators.setIsLoading, false);

      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }

      context.commit(BillingMutators.setPaymentMethods, result.cards);
    },
    async [BillingActions.deletePaymentMethod](context, paymentMethodId: string) {
      context.commit(BillingMutators.setIsLoading, true);
      const result = await makeApiRequest<DeletePaymentMethodRequest, DeletePaymentMethodResponse>(
        API_ENDPOINT.DeletePaymentMethod,
        {
          id: paymentMethodId,
        }
      );
      context.commit(BillingMutators.setIsLoading, false);

      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }
    },
    async [BillingActions.makePrimaryPaymentMethod](context, paymentMethodId: string) {
      context.commit(BillingMutators.setIsLoading, true);
      const result = await makeApiRequest<DeletePaymentMethodRequest, DeletePaymentMethodResponse>(
        API_ENDPOINT.MakePrimaryPaymentMethod,
        {
          id: paymentMethodId,
        }
      );
      context.commit(BillingMutators.setIsLoading, false);
      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }
    },
  }
};

export default BillingPaneModule;