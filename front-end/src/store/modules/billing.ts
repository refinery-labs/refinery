import {Module} from 'vuex';
import {RootState} from '../store-types';
import {makeApiRequest} from "@/store/fetchers/refinery-api";
import {
  AddPaymentMethodRequest, AddPaymentMethodResponse, BillChargeItem, BillingData, BillTotal,
  DeletePaymentMethodRequest,
  DeletePaymentMethodResponse, GetLatestMonthlyBillRequest, GetLatestMonthlyBillResponse,
  GetPaymentMethodsRequest,
  GetPaymentMethodsResponse
} from "@/types/api-types";
import {API_ENDPOINT} from "@/constants/api-constants";

// Enums
export enum BillingMutators {
  setPaymentMethods = 'setPaymentMethods',
  setisPaymentMethodsLoading = 'setisPaymentMethodsLoading',
  setMonthBillLoading = 'setMonthBillLoading',
  setMonthyBillingTotal = 'setMonthyBillingTotal',
  setBillingBreakDownArray = 'setBillingBreakDownArray'
}

export enum BillingActions {
  getPaymentMethods = 'getPaymentMethods',
  deletePaymentMethod = 'deletePaymentMethod',
  makePrimaryPaymentMethod = 'makePrimaryPaymentMethod',
  addPaymentMethod = 'addPaymentMethod',
  getMonthBill = 'getMonthBill'
}

// Types
export interface BillingPaneState {
  paymentMethods: PaymentMethodData[],
  isPaymentMethodsLoading: boolean,
  isMonthBillLoading: boolean,
  billingTotal: BillTotal,
  serviceBillingBreakDownArray: BillChargeItem[],
}

// Initial State
const moduleState: BillingPaneState = {
  paymentMethods: [],
  isPaymentMethodsLoading: true,
  isMonthBillLoading: true,
  billingTotal: {
    "bill_total": "0.00",
    "unit": "USD"
  },
  serviceBillingBreakDownArray: []
};

const BillingPaneModule: Module<BillingPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [BillingMutators.setPaymentMethods](state, results: PaymentMethodData[]) {
      state.paymentMethods = results;
    },
    [BillingMutators.setisPaymentMethodsLoading](state, isPaymentMethodsLoading: boolean) {
      state.isPaymentMethodsLoading = isPaymentMethodsLoading;
    },
    [BillingMutators.setMonthBillLoading](state, isMonthBillLoading: boolean) {
      state.isMonthBillLoading = isMonthBillLoading;
    },
    [BillingMutators.setMonthyBillingTotal](state, billingTotal: BillTotal) {
      state.billingTotal = billingTotal;
    },
    [BillingMutators.setBillingBreakDownArray](state, serviceBillingBreakDownArray: BillChargeItem[]) {
      state.serviceBillingBreakDownArray = serviceBillingBreakDownArray;
    },
  },
  actions: {
    async [BillingActions.getMonthBill](context, billingMonth: string) {
      context.commit(BillingMutators.setMonthBillLoading, true);
      const result = await makeApiRequest<GetLatestMonthlyBillRequest, GetLatestMonthlyBillResponse>(
        API_ENDPOINT.GetLatestMonthBill,
        {
          billing_month: billingMonth
        }
      );
      context.commit(BillingMutators.setMonthBillLoading, false);

      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get latest month\'s bill!');
        return;
      }

      context.commit(BillingMutators.setMonthyBillingTotal, result.billing_data);
      context.commit(BillingMutators.setBillingBreakDownArray, result.billing_data.service_breakdown);
    },
    async [BillingActions.getPaymentMethods](context) {
      context.commit(BillingMutators.setisPaymentMethodsLoading, true);
      const result = await makeApiRequest<GetPaymentMethodsRequest, GetPaymentMethodsResponse>(
        API_ENDPOINT.GetPaymentMethods,
        {}
      );
      context.commit(BillingMutators.setisPaymentMethodsLoading, false);

      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }

      context.commit(BillingMutators.setPaymentMethods, result.cards);
    },
    async [BillingActions.deletePaymentMethod](context, paymentMethodId: string) {
      context.commit(BillingMutators.setisPaymentMethodsLoading, true);
      const result = await makeApiRequest<DeletePaymentMethodRequest, DeletePaymentMethodResponse>(
        API_ENDPOINT.DeletePaymentMethod,
        {
          id: paymentMethodId,
        }
      );
      context.commit(BillingMutators.setisPaymentMethodsLoading, false);

      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }
    },
    async [BillingActions.makePrimaryPaymentMethod](context, paymentMethodId: string) {
      context.commit(BillingMutators.setisPaymentMethodsLoading, true);
      const result = await makeApiRequest<DeletePaymentMethodRequest, DeletePaymentMethodResponse>(
        API_ENDPOINT.MakePrimaryPaymentMethod,
        {
          id: paymentMethodId,
        }
      );
      context.commit(BillingMutators.setisPaymentMethodsLoading, false);
      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }
    },
    async [BillingActions.addPaymentMethod](context, stripeCardToken: string) {
      context.commit(BillingMutators.setisPaymentMethodsLoading, true);
      const result = await makeApiRequest<AddPaymentMethodRequest, AddPaymentMethodResponse>(
        API_ENDPOINT.AddPaymentMethod,
        {
          token: stripeCardToken,
        }
      );
      context.commit(BillingMutators.setisPaymentMethodsLoading, false);
      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failed to get payment methods!');
        return;
      }
    },
  }
};

export default BillingPaneModule;