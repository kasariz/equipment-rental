/**
 * Российский номер в маске +7 (900) 123-45-67.
 * Первая 8 или 7 считается кодом страны, лишние цифры отбрасываются.
 */

export function nationalDigits(input: string): string {
  let digits = input.replace(/\D/g, '')
  if (digits.startsWith('8') || digits.startsWith('7')) digits = digits.slice(1)
  return digits.slice(0, 10)
}

export function maskPhone(national: string): string {
  if (!national) return ''
  const d = national
  let out = '+7 (' + d.slice(0, 3)
  // Разделитель появляется только вместе со следующей цифрой: при стирании не остаётся висящих «-»
  if (d.length > 3) out += ') ' + d.slice(3, 6)
  if (d.length > 6) out += '-' + d.slice(6, 8)
  if (d.length > 8) out += '-' + d.slice(8, 10)
  return out
}

/**
 * Новое значение поля после ввода. Отдельно обрабатываем два случая:
 * - стёрли скобку или дефис — стираем последнюю цифру, иначе Backspace «не работает»;
 * - ввели только код страны (8 или +7) — показываем «+7 (», чтобы следующая цифра ушла в номер,
 *   а не снова считалась кодом страны (иначе в «8 (863)…» потерялась бы восьмёрка кода города)
 */
export function nextPhoneValue(previous: string, raw: string): string {
  const deleting = raw.length < previous.length
  let digits = nationalDigits(raw)
  if (deleting && digits === nationalDigits(previous)) digits = digits.slice(0, -1)
  if (digits === '') return !deleting && /\d/.test(raw) ? '+7 (' : ''
  return maskPhone(digits)
}

export function isCompletePhone(value: string): boolean {
  return nationalDigits(value).length === 10
}

/** +79001234567 из базы → +7 (900) 123-45-67 для показа */
export function formatPhone(phone: string): string {
  return /^\+7\d{10}$/.test(phone) ? maskPhone(phone.slice(2)) : phone
}
