import { ScClient } from 'ts-sc-client';

export const scClient = new ScClient('ws://localhost:8090/ws_json');

export async function connectSc() {
  await scClient.connect();
  console.log('✅ Connected to sc-server');
}
