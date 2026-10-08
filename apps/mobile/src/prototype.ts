export const categories = [
  { id: 'casa', name: 'Casa', color: '#315F51', subcategories: ['Aluguel', 'Internet', 'Energia'] },
  { id: 'alimentacao', name: 'Alimentação', color: '#BE6D45', subcategories: ['Mercado', 'Restaurantes', 'Café'] },
  { id: 'transporte', name: 'Transporte', color: '#647CAB', subcategories: ['Combustível', 'Aplicativos', 'Transporte público'] },
  { id: 'lazer', name: 'Lazer', color: '#A77EAC', subcategories: ['Passeios', 'Streaming', 'Compras'] },
] as const;

export type Expense = {
  id: string; cents: number; category: string; subcategory: string;
  date: string; payment: string; source: string; note: string;
};
export const accounts = ['Conta principal', 'Dinheiro'];
export const cards = ['Cartão do dia a dia', 'Cartão reserva'];
export const money = (cents: number) => (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
export const localDate = (date = new Date()) => `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
export const monthKey = (date: Date) => `${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;

export function validDate(value: string) {
  if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) return false;
  const [d, m, y] = value.split('/').map(Number);
  const date = new Date(y, m - 1, d);
  return date.getFullYear() === y && date.getMonth() === m - 1 && date.getDate() === d;
}

export function parseCents(value: string): number | null {
  const normalized = value.trim();
  if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/.test(normalized)) return null;
  const [whole, decimal = ''] = normalized.replaceAll('.', '').split(',');
  const cents = Number(whole) * 100 + Number(decimal.padEnd(2, '0'));
  return Number.isSafeInteger(cents) && cents > 0 && cents <= 999999999 ? cents : null;
}

export function initialExpenses(): Expense[] {
  const month = monthKey(new Date());
  return [
    { id: '1', cents: 150000, category: 'casa', subcategory: 'Aluguel', date: `01/${month}`, payment: 'Pix', source: accounts[0], note: 'Aluguel' },
    { id: '2', cents: 42000, category: 'alimentacao', subcategory: 'Mercado', date: `02/${month}`, payment: 'Débito', source: accounts[0], note: 'Compra da semana' },
    { id: '3', cents: 18000, category: 'transporte', subcategory: 'Combustível', date: `03/${month}`, payment: 'Pix', source: accounts[0], note: '' },
    { id: '4', cents: 9000, category: 'alimentacao', subcategory: 'Restaurantes', date: `04/${month}`, payment: 'Dinheiro', source: accounts[1], note: 'Almoço' },
    { id: '5', cents: 5990, category: 'lazer', subcategory: 'Streaming', date: `05/${month}`, payment: 'Crédito', source: cards[0], note: 'Assinatura' },
  ];
}
