<template>
  <div>
    <div class="content-heading display-flex billing-main-container">
      <div class="layout--constrain flex-grow--1">
        <div class="text-align--center">
          <!-- Payment methods card -->
          <div class="card b">
            <div class="card-header">
              <h2 class="my-2">
                <span>Billing Information</span>
              </h2>
            </div>
            <b-card-group>
              <div class="col-xl-6">
                <div class="card card-default" v-bind:class="{ 'whirl standard': isMonthBillLoading }">
                  <div class="card-header">
                    Current Billing Information for {{ getCurrentMonthHuman() }} <i>(Updated Daily)</i>
                    <div class="card-tool float-right" v-on:click="getLatestMonthBill">
                      <em class="fas fa-sync"></em>
                    </div>
                  </div>
                  <div class="table-responsive">
                    <table class="table table-striped table-bordered table-hover">
                      <tbody>
                        <tr v-for="BillChargeItem in serviceBillingBreakDownArray" v-bind:key="BillChargeItem">
                          <td class="text-align--left">{{ BillChargeItem.service_name }}</td>
                          <td class="text-align--right">${{ BillChargeItem.total }}</td>
                        </tr>
                        <tr class="table-info">
                          <td class="text-align--left">Total Bill Amount</td>
                          <td class="text-align--right">${{ billingTotal.bill_total }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div class="card-footer">
                    <small
                      >Please note this bill may not be up to date. You can generally expect your billing totals to be
                      refreshed every 24 hours. For help with your bill, or for more information, contact
                      <code>billing@refinery.io</code>
                    </small>
                  </div>
                </div>
              </div>
              <div class="col-xl-6">
                <div class="card card-default" v-bind:class="{ 'whirl standard': isPaymentMethodsLoading }">
                  <div class="card-header">
                    Payment Methods
                    <div class="card-tool float-right" v-on:click="getCards"><em class="fas fa-sync"></em></div>
                  </div>
                  <div class="table-responsive">
                    <table class="table table-striped table-bordered table-hover">
                      <tbody>
                        <tr v-for="paymentMethod in paymentMethods" v-bind:key="paymentMethod">
                          <td>
                            <div class="media align-items-center">
                              <div class="media-body d-flex">
                                <div class="media-body d-flex ml-auto">
                                  <h4 class="m-0 p-2">
                                    <em
                                      v-if="paymentMethod.brand.toLowerCase() === 'mastercard'"
                                      class="fab fa-cc-mastercard"
                                    ></em>
                                    <em v-if="paymentMethod.brand.toLowerCase() === 'amex'" class="fab fa-cc-amex"></em>
                                    <em
                                      v-if="paymentMethod.brand.toLowerCase() === 'diners'"
                                      class="fab fa-cc-diners-club"
                                    ></em>
                                    <em
                                      v-if="paymentMethod.brand.toLowerCase() === 'discover'"
                                      class="fab fa-cc-discover"
                                    ></em>
                                    <em v-if="paymentMethod.brand.toLowerCase() === 'jcb'" class="fab fa-cc-jcb"></em>
                                    <em
                                      v-if="paymentMethod.brand.toLowerCase() === 'unionpay'"
                                      class="fab fa-credit-card"
                                    ></em>
                                    <em v-if="paymentMethod.brand.toLowerCase() === 'visa'" class="fab fa-cc-visa"></em>
                                    <em
                                      v-if="paymentMethod.brand.toLowerCase() === 'unknown'"
                                      class="fab fa-credit-card"
                                    ></em>
                                    •••• •••• •••• {{ paymentMethod.last4 }}
                                    <i
                                      >{{ paymentMethod.exp_month.toString() }}/{{
                                        paymentMethod.exp_year.toString()
                                      }}</i
                                    >
                                    <div
                                      class="px-2 mr-2 float-left badge badge-success"
                                      v-if="paymentMethod.is_primary"
                                    >
                                      Primary
                                    </div>
                                    <div
                                      class="px-2 mr-2 float-left badge badge-secondary"
                                      v-if="!paymentMethod.is_primary"
                                    >
                                      Secondary
                                    </div>
                                  </h4>
                                </div>
                                <div class="billing-buttons-column align-items-right">
                                  <button
                                    v-if="!paymentMethod.is_primary"
                                    type="button"
                                    class="btn btn-primary billing-button"
                                    v-on:click="makePrimaryCard(paymentMethod)"
                                  >
                                    <span class="fas fa-check-circle"></span> Make Primary
                                  </button>
                                  <button
                                    v-if="!paymentMethod.is_primary"
                                    type="button"
                                    class="btn btn-danger billing-button"
                                    v-on:click="deleteCard(paymentMethod)"
                                  >
                                    <span class="fas fa-trash"></span>
                                  </button>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div class="card-footer">
                    <label class="text-muted d-block" htmlFor="user-name-input">
                      Add New Payment Method
                    </label>
                    <StripeAddPaymentCard v-bind:setRegistrationStripeTokenValue="setStripeToken" />
                  </div>
                </div>
              </div>
            </b-card-group>
          </div>
          <h4>
            To cancel your billing, please click <a :href="getEmailLink()" target="_blank">here</a> (or send an email to
            support@refinery.io).
          </h4>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { namespace } from 'vuex-class';
import { BillChargeItem, BillTotal, PaymentCardResult } from '@/types/api-types';
import StripeAddPaymentCard from '@/components/Common/StripeAddPaymentCard.vue';
import moment from 'moment';

const billing = namespace('billing');
const user = namespace('user');

@Component({
  components: {
    StripeAddPaymentCard
  }
})
export default class Billing extends Vue {
  @billing.Action getPaymentMethods!: () => void;
  @billing.Action deletePaymentMethod!: (paymentMethodId: string) => void;
  @billing.Action makePrimaryPaymentMethod!: (paymentMethodId: string) => void;
  @billing.Action addPaymentMethod!: (paymentMethodId: string) => void;
  @billing.Action getMonthBill!: (billingMonth: string) => void;

  @billing.State billingTotal!: () => BillTotal;
  @billing.State serviceBillingBreakDownArray!: () => BillChargeItem[];
  @billing.State paymentMethods!: () => PaymentCardResult[];
  @billing.State isPaymentMethodsLoading!: () => Boolean;
  @billing.State isMonthBillLoading!: () => Boolean;

  @user.State email!: string | null;

  getCurrentMonthHuman() {
    return moment().format('MMMM YYYY');
  }

  async getLatestMonthBill() {
    await this.getMonthBill(moment().format('YYYY-MM'));
  }

  getEmailLink() {
    const userEmail = this.email ? this.email : 'Please put your Refinery email here';

    return `mailto:support@refinery.io?subject=Cancel%20Subscription%20Request&body=${encodeURIComponent(userEmail)}`;
  }

  async setStripeToken(paymentTokenId: string) {
    // Add this card to our payment methods
    await this.addPaymentMethod(paymentTokenId);

    // Update the payment methods
    await this.getPaymentMethods();
  }

  async makePrimaryCard(paymentMethod: PaymentCardResult) {
    // Make this our primary payment method
    await this.makePrimaryPaymentMethod(paymentMethod.id);

    // Update the payment methods
    await this.getPaymentMethods();
  }

  async deleteCard(paymentMethod: PaymentCardResult) {
    // Delete the card
    await this.deletePaymentMethod(paymentMethod.id);

    // Update the payment methods now that the card is deleted.
    await this.getPaymentMethods();
  }

  async getCards() {
    await this.getPaymentMethods();
  }

  async mounted() {
    this.getPaymentMethods();
    this.getLatestMonthBill();
  }
}
</script>
