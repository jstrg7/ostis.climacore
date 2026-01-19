declare module 'ts-sc-client' {
  // минимальные подписи -- расширяй по необходимости
  export class ScClient {
    constructor(url: string);
    connect(): Promise<void>;
    // добавь методы, которые реально используешь
    execute(...args: any[]): Promise<any>;
    on(event: string, handler: (...args: any[]) => void): void;
  }
  export default ScClient;
}
