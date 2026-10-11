export type Subcategory = { id: string; name: string; active: boolean };
export type Category = {
  id: string; name: string; color: string; active: boolean; subcategories: Subcategory[];
};
export type Account = {
  id: string; name: string; kind: 'bank' | 'cash'; balance_cents: number; opened_on: string;
};
export type Expense = {
  id: string; account_id: string; category_id: string; subcategory_id: string;
  amount_cents: number; occurred_on: string;
  payment_method: 'pix' | 'debit' | 'cash' | 'credit'; note: string;
  card_name?: string; sequence?: number; total_count?: number; invoice_paid?: boolean;
};
export type ExpenseInput = Omit<Expense, 'id'>;
export const dateToIso = (value: string) => value.split('/').reverse().join('-');
export const dateToDisplay = (value: string) => value.split('-').reverse().join('/');
export const monthIso = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
export const paymentLabel = { pix: 'Pix', debit: 'Débito', cash: 'Dinheiro', credit: 'Crédito' };

export type CreditCard = {
  id: string; name: string; closing_day: number; due_day: number;
  closing_day_next_bill: boolean; active: boolean;
};
export type CardInstallment = {
  id: string; purchase_id: string; card_id: string; card_name: string;
  invoice_id: string; invoice_month: string; invoice_paid: boolean;
  purchased_on: string; legacy: boolean; sequence: number; total_count: number;
  amount_cents: number; category_id: string; subcategory_id: string; note: string;
};
export type Invoice = {
  id: string; card_id: string; card_name: string; month: string;
  closes_on: string; due_on: string; paid_on: string | null;
  status: 'open' | 'closed' | 'paid' | 'refinanced'; total_cents: number;
  purchase_total_cents: number; financed_total_cents: number;
  installments: CardInstallment[];
  financing_installments: FinancingInstallment[];
  financing: null | {
    id: string; paid_cents: number; principal_cents: number;
    fee_cents: number; installment_count: number;
  };
};
export type CardPurchaseInput = {
  card_id: string; category_id: string; subcategory_id: string;
  purchased_on: string; total_cents: number; installment_count: number;
  note: string; legacy: boolean; first_bill_month?: string;
  first_sequence?: number;
};

export type FinancingInstallment = {
  id: string; financing_id: string; source_invoice_id: string;
  invoice_id: string; invoice_month: string; invoice_paid: boolean;
  card_id: string; card_name: string; sequence: number; total_count: number;
  principal_cents: number; fee_cents: number; amount_cents: number;
};
