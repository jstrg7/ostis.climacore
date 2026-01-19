import { scClient } from './client';

export async function setTemperature(device: string, value: number) {
  // TODO: здесь реальные sc-операции
  // например: создать узел состояния и связать с устройством
  console.log(`🔥 setTemperature ${device} = ${value}`);
}

export async function askQuestion(text: string): Promise<string> {
  // TODO: sc-поиск / агент
  return `Я получил вопрос: ${text}`;
}
