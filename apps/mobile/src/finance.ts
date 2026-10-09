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
  payment_method: 'pix' | 'debit' | 'cash'; note: string;
};
export type ExpenseInput = Omit<Expense, 'id'>;
export const dateToIso = (value: string) => value.split('/').reverse().join('-');
export const dateToDisplay = (value: string) => value.split('-').reverse().join('/');
export const monthIso = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
export const paymentLabel = { pix: 'Pix', debit: 'Débito', cash: 'Dinheiro' };
