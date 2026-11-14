import type { Lang } from '../i18n'

/** Assistant UI texts (EN / RO). Replies themselves come from the backend in the user's language. */
const en = {
  open: 'Ask the assistant',
  title: 'Assistant',
  badge: 'AI',
  close: 'Close',
  clear: 'New chat',
  placeholder: 'Ask about an area, crop, risk or rotation…',
  send: 'Send',
  thinking: 'Looking at the data…',
  intro: 'Hi! I answer from this dashboard’s data and can move the map for you. Type a commune or county name, or try one of these:',
  offlineNote: 'AI is off: I can still find places and open sections.',
  wait: 'Please wait {n} s',
  netError: 'Could not reach the assistant. Check your connection and try again.',
  aiTag: 'AI answer · can be wrong · check the panel',
  ruleTag: 'From the data (no AI)',
  sources: 'Sources',
  unverified: 'Not found in the data',
  pickOne: 'Select',
  did: 'Dashboard updated',
  role: 'What this assistant does: it finds areas, opens sections, colours the map and explains the numbers already in this dashboard. Place names and simple commands (“open soil”) are handled by fixed code. Other questions go to Google Gemini, which can only read this project’s data through fixed read-only tools: it does not forecast, does not add data and cannot change anything except your view.\n\nWhere it fails: it can misread a question, pick the wrong one of two communes with the same name, or word a number loosely. Figures it cannot match to the data are flagged with ⚠. Coarse grids (POWER ~50 km) describe the region, not your field. Always check the numbers in the panel.\n\nPrivacy: questions that need AI are sent to Google Gemini; this app does not store them. Limits: 500 characters per message and a few messages per minute.',
  suggestFarmer: ['Hot days at maize flowering here in 2024', 'Compare maize–wheat–maize with pea–wheat–sunflower here', 'What is the soil like here?', 'Which commune in Alba had the driest summer in 2024?'],
  suggestProcurement: ['Where is pea supply most reliable?', 'Weather quality risks for maize in the latest season', 'Show oats availability on the map', 'Which counties grow the most sunflower?'],
}

export type AssistantText = typeof en

const ro: AssistantText = {
  open: 'Întrebați asistentul',
  title: 'Asistent',
  badge: 'AI',
  close: 'Închide',
  clear: 'Conversație nouă',
  placeholder: 'Întrebați despre o zonă, cultură, risc sau rotație…',
  send: 'Trimite',
  thinking: 'Mă uit în date…',
  intro: 'Bună! Răspund din datele acestui panou și pot muta harta pentru dvs. Scrieți numele unei comune sau al unui județ, sau încercați:',
  offlineNote: 'AI-ul este oprit: pot totuși găsi locuri și deschide secțiuni.',
  wait: 'Așteptați {n} s',
  netError: 'Asistentul nu poate fi contactat. Verificați conexiunea și încercați din nou.',
  aiTag: 'Răspuns AI · poate greși · verificați în panou',
  ruleTag: 'Din date (fără AI)',
  sources: 'Surse',
  unverified: 'Negăsit în date',
  pickOne: 'Selectează',
  did: 'Panoul a fost actualizat',
  role: 'Ce face asistentul: găsește zone, deschide secțiuni, colorează harta și explică cifrele deja prezente în panou. Numele de locuri și comenzile simple („deschide solul”) sunt tratate de cod fix. Celelalte întrebări merg la Google Gemini, care poate citi doar datele proiectului prin instrumente fixe, numai-citire: nu face prognoze, nu adaugă date și nu poate schimba nimic în afară de vizualizarea dvs.\n\nUnde greșește: poate înțelege greșit o întrebare, poate alege greșit între două comune cu același nume sau poate formula vag o cifră. Cifrele care nu se regăsesc în date sunt marcate cu ⚠. Grilele mari (POWER ~50 km) descriu regiunea, nu parcela. Verificați mereu cifrele în panou.\n\nConfidențialitate: întrebările care necesită AI sunt trimise la Google Gemini; aplicația nu le stochează. Limite: 500 de caractere pe mesaj și câteva mesaje pe minut.',
  suggestFarmer: ['Zile caniculare la înflorirea porumbului aici în 2024', 'Compară porumb–grâu–porumb cu mazăre–grâu–floarea-soarelui aici', 'Cum este solul aici?', 'Care comună din Alba a avut cea mai secetoasă vară în 2024?'],
  suggestProcurement: ['Unde este aprovizionarea cu mazăre cea mai sigură?', 'Riscuri de calitate pentru porumb în ultimul sezon', 'Arată disponibilitatea ovăzului pe hartă', 'Care județe cultivă cea mai multă floarea-soarelui?'],
}

export const ASSISTANT_TEXT: Record<Lang, AssistantText> = { en, ro }
