export function formatMoneyInput(raw: string, previous = ''): string {
  if (previous === '0,00' && raw === '0,0') return '';
  const digits = raw.replace(/\D/g, '');
  if (!digits) return '';
  if (digits.length > 9) return previous;
  return (Number(digits) / 100).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
